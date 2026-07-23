from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from common import REPORTS_DIR, load_catalog


def inspect_pdf(paper: dict, timeout: int) -> dict:
    url = paper["source_pdf_url"]
    request = Request(url, method="HEAD", headers={"User-Agent": "WERpapers PDF audit/1.0"})
    result = {"id": paper["id"], "year": paper["year"], "title": paper["title"], "url": url}
    try:
        with urlopen(request, timeout=timeout) as response:
            length = response.headers.get("Content-Length", "")
            result.update(
                status=response.status,
                content_type=response.headers.get_content_type(),
                bytes=int(length) if length.isdigit() else None,
                final_url=response.geturl(),
            )
    except HTTPError as exc:
        result.update(status=exc.code, error=str(exc))
    except (URLError, TimeoutError, OSError) as exc:
        result.update(status=None, error=str(exc))
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit remote WERpapers PDF headers")
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()
    papers = load_catalog()["papers"]
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(inspect_pdf, paper, args.timeout): paper["id"] for paper in papers}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda item: (item["year"], item["id"]))
    oversized = [item for item in results if (item.get("bytes") or 0) > 5 * 1024 * 1024]
    unavailable = [item for item in results if item.get("status") != 200]
    wrong_type = [item for item in results if item.get("status") == 200 and item.get("content_type") != "application/pdf"]
    unknown_size = [item for item in results if item.get("status") == 200 and item.get("bytes") is None]
    summary = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "available": len(results) - len(unavailable),
        "unavailable": len(unavailable),
        "over_5_mib": len(oversized),
        "wrong_content_type": len(wrong_type),
        "unknown_size": len(unknown_size),
        "total_bytes": sum(item.get("bytes") or 0 for item in results),
        "largest": sorted((item for item in results if item.get("bytes") is not None), key=lambda item: item["bytes"], reverse=True)[:20],
    }
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "remote-pdf-audit.json").write_text(
        json.dumps({"summary": summary, "oversized": oversized, "unavailable": unavailable, "wrong_content_type": wrong_type, "results": results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# Auditoría remota de PDFs", "",
        f'- Comprobados: {summary["total"]}',
        f'- Disponibles: {summary["available"]}',
        f'- No disponibles: {summary["unavailable"]}',
        f'- Mayores de 5 MiB: {summary["over_5_mib"]}',
        f'- Tipo distinto de application/pdf: {summary["wrong_content_type"]}',
        f'- Tamaño desconocido: {summary["unknown_size"]}', "",
    ]
    if oversized:
        lines += ["## Mayores de 5 MiB", ""] + [f'- {item["id"]}: {item["bytes"] / 1024 / 1024:.2f} MiB — {item["title"]}' for item in oversized] + [""]
    if unavailable:
        lines += ["## No disponibles", ""] + [f'- {item["id"]}: HTTP {item.get("status")} — {item["url"]}' for item in unavailable] + [""]
    (REPORTS_DIR / "remote-pdf-audit.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
