from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
REPORTS_DIR = ROOT / "reports"
CATALOG_PATH = DATA_DIR / "catalog.json"

# Keep the historical public origin exactly as it is already cited and indexed.
# HTTPS can be added by the university later, but must not replace these HTTP URLs
# unless every historical address is kept available or redirected one-to-one.
PUC_BASE = "http://wer.inf.puc-rio.br/WERpapers"
UFRN_BASE = "https://werpapers.dimap.ufrn.br"


def load_catalog() -> dict:
    with CATALOG_PATH.open(encoding="utf-8") as stream:
        return json.load(stream)


def save_catalog(catalog: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with CATALOG_PATH.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(catalog, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def compact_year(year: int | str) -> str:
    return f"{int(year) % 100:02d}"


def legacy_folder(year: int | str) -> str:
    return f"artigos/artigos_WER{compact_year(year)}"


def pdf_filename(pdf_url: str) -> str:
    return Path(urlparse(pdf_url).path).name


def paper_filename(paper: dict) -> str:
    source_name = Path(urlparse(paper["source_page_url"]).path).name
    return source_name or f'{paper["id"]}.html'


def paper_relative_url(paper: dict) -> str:
    return f'{legacy_folder(paper["year"])}/{paper_filename(paper)}'


def pdf_relative_url(paper: dict) -> str:
    return f'{legacy_folder(paper["year"])}/{pdf_filename(paper["source_pdf_url"])}'


def absolute_puc(relative_url: str) -> str:
    return f"{PUC_BASE}/{relative_url.lstrip('/')}"


def split_pages(value: str) -> tuple[str, str]:
    value = (value or "").strip()
    match = re.match(r"^\s*([ivxlcdm\d]+)\s*[-–—]\s*([ivxlcdm\d]+)\s*$", value, re.I)
    return (match.group(1), match.group(2)) if match else ("", "")


def h(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def slug_id(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
