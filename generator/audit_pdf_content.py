from __future__ import annotations

import argparse
import io
import json
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pypdf import PdfReader

from common import REPORTS_DIR, load_catalog


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.encode("ascii", "ignore").decode().lower()).split())


def title_coverage(title: str, text: str) -> float:
    title_words = {word for word in normalize(title).split() if len(word) > 2}
    text_words = set(normalize(text).split())
    return len(title_words & text_words) / len(title_words) if title_words else 0.0


def inspect(paper: dict, timeout: int) -> dict:
    result = {"id": paper["id"], "year": paper["year"], "title": paper["title"], "url": paper["source_pdf_url"]}
    request = Request(paper["source_pdf_url"], headers={"User-Agent": "WERpapers PDF content audit/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
        reader = PdfReader(io.BytesIO(payload))
        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except Exception:
                pass
        first_text = (reader.pages[0].extract_text() or "") if reader.pages else ""
        last_text = "\n".join((page.extract_text() or "") for page in reader.pages[-3:]) if reader.pages else ""
        surnames = [normalize(author).split()[-1] for author in paper.get("authors", []) if normalize(author)]
        normalized_first = set(normalize(first_text).split())
        result.update(
            status=200,
            bytes=len(payload),
            pages=len(reader.pages),
            encrypted=reader.is_encrypted,
            first_page_chars=len(first_text.strip()),
            title_coverage=round(title_coverage(paper["title"], first_text), 3),
            author_surnames_found=sum(surname in normalized_first for surname in surnames),
            author_count=len(surnames),
            references_heading=bool(re.search(r"(?im)^\s*(references|bibliography|referencias|referências)\s*$", last_text)),
        )
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, Exception) as exc:
        result.update(status=getattr(exc, "code", None), error=f"{type(exc).__name__}: {exc}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit text extraction from remote WERpapers PDFs")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    papers = load_catalog()["papers"]
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(inspect, paper, args.timeout) for paper in papers]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (item["year"], item["id"]))
    failed = [item for item in results if item.get("status") != 200]
    no_text = [item for item in results if item.get("status") == 200 and item.get("first_page_chars", 0) < 100]
    weak_title = [item for item in results if item.get("status") == 200 and item.get("title_coverage", 0) < 0.6]
    weak_authors = [item for item in results if item.get("status") == 200 and item.get("author_count", 0) and item.get("author_surnames_found", 0) == 0]
    no_references = [item for item in results if item.get("status") == 200 and not item.get("references_heading")]
    summary = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "readable": len(results) - len(failed),
        "failed": len(failed),
        "first_page_under_100_chars": len(no_text),
        "title_coverage_under_60_percent": len(weak_title),
        "no_author_surname_found": len(weak_authors),
        "no_reference_heading_detected": len(no_references),
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "pdf-content-audit.json").write_text(
        json.dumps({"summary": summary, "failed": failed, "no_text": no_text, "weak_title": weak_title, "weak_authors": weak_authors, "no_references": no_references, "results": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
