from __future__ import annotations

import argparse
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from common import UFRN_BASE, pdf_filename, save_catalog


def clean_html_fragment(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def parse_committees(html_text: str) -> list[dict]:
    section_match = re.search(r'<section[^>]*class=["\']masthead_table["\'][^>]*>(.*?)</section>', html_text, re.I | re.S)
    if not section_match:
        return []
    section = section_match.group(1)
    headings = list(re.finditer(r"<h4[^>]*>(.*?)</h4>", section, re.I | re.S))
    committees = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(section)
        segment = section[heading.end():end]
        members = [clean_html_fragment(item) for item in re.findall(r"<li[^>]*>(.*?)</li>", segment, re.I | re.S)]
        members = [member for member in members if member]
        if members:
            committees.append({"name": clean_html_fragment(heading.group(1)), "members": members})
    return committees


class EditionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self._in_title = False
        self._href = ""
        self._anchor_text: list[str] = []
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        if tag == "a" and attrs_dict.get("href"):
            self._href = attrs_dict["href"] or ""
            self._anchor_text = []

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        if self._href:
            self._anchor_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "a" and self._href:
            self.links.append((self._href, "".join(self._anchor_text).strip()))
            self._href = ""
            self._anchor_text = []


class PaperParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, list[str]] = {}
        self.abstracts: list[str] = []
        self._capture_abstract = False
        self._abstract_buffer: list[str] = []
        self._capture_pre = False
        self._pre_buffer: list[str] = []
        self.pre_blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "meta" and attrs_dict.get("name") and attrs_dict.get("content") is not None:
            key = (attrs_dict["name"] or "").lower()
            self.meta.setdefault(key, []).append(attrs_dict["content"] or "")
        classes = set((attrs_dict.get("class") or "").split())
        if tag == "p" and "abstract" in classes:
            self._capture_abstract = True
            self._abstract_buffer = []
        if tag == "pre":
            self._capture_pre = True
            self._pre_buffer = []

    def handle_data(self, data: str) -> None:
        if self._capture_abstract:
            self._abstract_buffer.append(data)
        if self._capture_pre:
            self._pre_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "p" and self._capture_abstract:
            text = " ".join("".join(self._abstract_buffer).split())
            if text:
                self.abstracts.append(text)
            self._capture_abstract = False
        if tag == "pre" and self._capture_pre:
            text = "".join(self._pre_buffer).strip()
            if text:
                self.pre_blocks.append(text)
            self._capture_pre = False

    def one(self, name: str) -> str:
        values = self.meta.get(name.lower(), [])
        return values[0].strip() if values else ""


def fetch(url: str, attempts: int = 3) -> str:
    request = Request(url, headers={"User-Agent": "WERpapers static importer/1.0"})
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except (HTTPError, URLError, TimeoutError):
            if attempt == attempts - 1:
                raise
            time.sleep(1 + attempt)
    raise RuntimeError(f"No se pudo descargar {url}")


def parse_paper(html_text: str, page_url: str, fallback_pdf: str, year: int, paper_id: str) -> dict:
    parser = PaperParser()
    parser.feed(html_text)
    abstract = parser.abstracts[0] if parser.abstracts else parser.one("dc.description")
    keywords = ""
    for candidate in parser.abstracts[1:]:
        if candidate.lower().startswith("keywords:"):
            keywords = candidate.split(":", 1)[1].strip()
            break
    keywords = keywords or parser.one("citation_keywords")
    publication_date = parser.one("citation_publication_date") or parser.one("dc.date")
    return {
        "id": paper_id,
        "year": year,
        "title": parser.one("citation_title") or parser.one("dc.title"),
        "authors": parser.meta.get("citation_author", []) or parser.meta.get("dc.creator", []),
        "publication_date": publication_date,
        "doi": parser.one("citation_doi"),
        "issn": parser.one("citation_issn") or "2675-0066",
        "isbn": parser.one("citation_isbn"),
        "conference_title": parser.one("citation_conference_title") or "Workshop on Requirements Engineering (WER)",
        "conference_location": parser.one("citation_conference_location"),
        "section": parser.one("citation_section"),
        "pages": parser.one("citation_pages"),
        "abstract": abstract,
        "keywords": keywords,
        "language": parser.meta.get("citation_title", [""])[0] and "" or "",
        "bibtex": parser.pre_blocks[-1] if parser.pre_blocks else "",
        "source_page_url": page_url,
        "source_pdf_url": parser.one("citation_pdf_url") or fallback_pdf,
    }


def edition_year(path: Path) -> int:
    match = re.search(r"(19|20)\d{2}", path.stem)
    if not match:
        raise ValueError(f"No se reconoce el año de {path}")
    return int(match.group(0))


def main() -> None:
    arg_parser = argparse.ArgumentParser(description="Importa el catálogo plano de WERpapers UFRN")
    arg_parser.add_argument("--editions-dir", type=Path, required=True)
    arg_parser.add_argument("--fetch-pages", action="store_true")
    arg_parser.add_argument("--cache-dir", type=Path, default=Path(__file__).resolve().parents[1] / "cache" / "pages")
    args = arg_parser.parse_args()
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    editions = []
    records: list[dict] = []
    seen_pages: set[str] = set()
    for edition_path in sorted(args.editions_dir.glob("wer[12][0-9][0-9][0-9].html")):
        year = edition_year(edition_path)
        edition_code = f"WER{year}"
        edition_html = edition_path.read_text(encoding="utf-8")
        parser = EditionParser()
        parser.feed(edition_html)
        edition_info: dict[str, str] = {}
        info_match = re.search(r'<ul[^>]*class=["\']edition-info["\'][^>]*>(.*?)</ul>', edition_html, re.I | re.S)
        if info_match:
            for item in re.findall(r"<li[^>]*>(.*?)</li>", info_match.group(1), re.I | re.S):
                text = clean_html_fragment(item)
                if ":" in text:
                    name, value = text.split(":", 1)
                    edition_info[name.strip().lower()] = value.strip()
        editors_match = re.search(r'<ul[^>]*class=["\']editors["\'][^>]*>(.*?)</ul>', edition_html, re.I | re.S)
        editors = clean_html_fragment(editors_match.group(1)) if editors_match else ""
        editors = re.sub(r"\)\s+(?=[A-ZÁÉÍÓÚ])", "); ", editors)
        committees = parse_committees(edition_html)
        contact_emails = sorted(set(re.findall(r'mailto:([^"\'>\s]+)', edition_html, re.I)))
        location_and_date = edition_info.get("location and date", "")
        page_links: list[dict] = []
        current: dict | None = None
        for href, text in parser.links:
            if re.search(rf"/proceedings/{edition_code}/wer[^/]+\.html$", href) and not href.endswith(f"/wer{year}.html"):
                current = {"page_url": href, "title": text, "pdf_url": ""}
                page_links.append(current)
            elif current is not None and re.search(rf"/papers/{edition_code}/.+\.pdf$", href, re.I) and not current["pdf_url"]:
                current["pdf_url"] = href
        edition_papers = []
        for link in page_links:
            page_url = link["page_url"]
            if page_url in seen_pages:
                continue
            seen_pages.add(page_url)
            paper_id = Path(page_url).stem
            cache_path = args.cache_dir / edition_code / f"{paper_id}.html"
            records.append({"page_url": page_url, "fallback_title": link["title"], "fallback_pdf": link["pdf_url"], "year": year, "paper_id": paper_id, "cache_path": cache_path})
            edition_papers.append(paper_id)
        editions.append({
            "code": edition_code,
            "year": year,
            "title": " ".join(parser.title.split()),
            "edition_number": year - 1997,
            "location_and_date": location_and_date,
            "issn": edition_info.get("issn", "2675-0066"),
            "isbn": edition_info.get("isbn", ""),
            "publisher": edition_info.get("publisher", ""),
            "editors": editors,
            "committees": committees,
            "contact_email": contact_emails[0] if contact_emails else "",
            "source_file": str(edition_path),
            "source_url": f"{UFRN_BASE}/proceedings/{edition_code}/wer{year}.html",
            "paper_ids": edition_papers,
        })

    if args.fetch_pages:
        pending = [record for record in records if not record["cache_path"].exists()]

        def download(record: dict) -> str:
            record["cache_path"].parent.mkdir(parents=True, exist_ok=True)
            record["cache_path"].write_text(fetch(record["page_url"]), encoding="utf-8")
            return record["page_url"]

        with ThreadPoolExecutor(max_workers=12) as executor:
            futures = {executor.submit(download, record): record for record in pending}
            for index, future in enumerate(as_completed(futures), 1):
                future.result()
                if index % 50 == 0 or index == len(pending):
                    print(f"Descargadas {index}/{len(pending)} páginas")

    papers = []
    for record in records:
        if record["cache_path"].exists():
            paper = parse_paper(
                record["cache_path"].read_text(encoding="utf-8"),
                record["page_url"],
                record["fallback_pdf"],
                record["year"],
                record["paper_id"],
            )
        else:
            paper = {
                "id": record["paper_id"], "year": record["year"], "title": record["fallback_title"],
                "authors": [], "publication_date": str(record["year"]), "doi": "", "issn": "2675-0066",
                "isbn": "", "conference_title": "Workshop on Requirements Engineering (WER)",
                "conference_location": "", "section": "", "pages": "", "abstract": "", "keywords": "",
                "language": "", "bibtex": "", "source_page_url": record["page_url"],
                "source_pdf_url": record["fallback_pdf"],
            }
        papers.append(paper)

    catalog = {
        "repository": {
            "name": "WERpapers",
            "publisher": "PUC-Rio",
            "base_url": "http://wer.inf.puc-rio.br/WERpapers",
            "issn": "2675-0066",
        },
        "editions": editions,
        "papers": papers,
    }
    save_catalog(catalog)
    print(f"Importadas {len(editions)} ediciones y {len(papers)} publicaciones")


if __name__ == "__main__":
    main()
