from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree

from common import REPORTS_DIR, SITE_DIR, absolute_puc, legacy_folder, load_catalog, paper_relative_url, pdf_relative_url


def main() -> None:
    parser = argparse.ArgumentParser(description="Valida la salida estática de WERpapers")
    parser.add_argument("--pdf-root", type=Path, help="Raíz opcional que contiene los PDFs para comprobar tamaño y presencia")
    args = parser.parse_args()
    catalog = load_catalog()
    errors: list[str] = []
    warnings: list[str] = []

    required = ("title", "authors", "publication_date", "abstract", "source_pdf_url")
    page_paths = [paper_relative_url(paper) for paper in catalog["papers"]]
    pdf_paths = [pdf_relative_url(paper) for paper in catalog["papers"]]
    for label, values in (("página", page_paths), ("PDF", pdf_paths)):
        for value, count in Counter(values).items():
            if count > 1:
                errors.append(f"Ruta de {label} duplicada: {value} ({count})")

    for paper in catalog["papers"]:
        for field in required:
            if not paper.get(field):
                errors.append(f'{paper["id"]}: falta {field}')
        page_path = SITE_DIR / paper_relative_url(paper)
        if not page_path.exists():
            errors.append(f"No se generó {page_path.relative_to(SITE_DIR)}")
            continue
        markup = page_path.read_text(encoding="utf-8")
        expected = {
            'name="citation_title"': "citation_title",
            'name="citation_author"': "citation_author",
            'name="citation_publication_date"': "citation_publication_date",
            'name="citation_pdf_url"': "citation_pdf_url",
            'rel="canonical"': "canonical",
            'application/ld+json': "JSON-LD",
        }
        for needle, label in expected.items():
            if needle not in markup:
                errors.append(f'{paper["id"]}: falta {label} en HTML')
        expected_pdf = absolute_puc(pdf_relative_url(paper))
        if expected_pdf not in markup:
            errors.append(f'{paper["id"]}: citation_pdf_url no conserva la ruta histórica')
        if f'href="{expected_pdf}"' not in markup:
            errors.append(f'{paper["id"]}: el botón PDF no usa la URL pública histórica')
        if Path(paper_relative_url(paper)).parent != Path(pdf_relative_url(paper)).parent:
            errors.append(f'{paper["id"]}: HTML y PDF no están en el mismo directorio')
        if "https://scholar.google.com/scholar?q=" not in markup:
            errors.append(f'{paper["id"]}: falta enlace de búsqueda en Google Scholar')
        if args.pdf_root:
            pdf_path = args.pdf_root / pdf_relative_url(paper)
            if not pdf_path.exists():
                warnings.append(f'{paper["id"]}: PDF no encontrado en el paquete local')
            elif pdf_path.stat().st_size > 5 * 1024 * 1024:
                warnings.append(f'{paper["id"]}: PDF supera 5 MiB ({pdf_path.stat().st_size} bytes)')

    for edition in catalog["editions"]:
        year = edition["year"]
        if not edition.get("contact_email"):
            errors.append(f"WER{year}: falta contacto")
        if not edition.get("committees"):
            errors.append(f"WER{year}: falta expediente")
        masthead_path = SITE_DIR / legacy_folder(year) / "expediente.html"
        if not masthead_path.exists():
            errors.append(f"WER{year}: no se generó expediente.html")

    anais_path = SITE_DIR / "anais.html"
    if not anais_path.exists():
        errors.append("No se generó anais.html")
    else:
        anais_markup = anais_path.read_text(encoding="utf-8")
        for anchor in ("presentacion", "normas", "expediente", "ediciones", "contacto"):
            if f'id="{anchor}"' not in anais_markup:
                errors.append(f"Anais: falta la sección {anchor}")
        if "2675-0066" not in anais_markup:
            errors.append("Anais: falta ISSN 2675-0066")

    sitemap_path = SITE_DIR / "sitemap.xml"
    try:
        tree = ElementTree.parse(sitemap_path)
        locations = {node.text for node in tree.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
        for paper in catalog["papers"]:
            for url in (absolute_puc(paper_relative_url(paper)), absolute_puc(pdf_relative_url(paper))):
                if url not in locations:
                    errors.append(f"Falta en sitemap: {url}")
        for edition in catalog["editions"]:
            url = absolute_puc(f'{legacy_folder(edition["year"])}/expediente.html')
            if url not in locations:
                errors.append(f"Falta en sitemap: {url}")
        if absolute_puc("anais.html") not in locations:
            errors.append(f"Falta en sitemap: {absolute_puc('anais.html')}")
    except (OSError, ElementTree.ParseError) as exc:
        errors.append(f"Sitemap inválido: {exc}")

    home_markup = (SITE_DIR / "index.html").read_text(encoding="utf-8")
    if "https://dblp.org/db/conf/wer/index.html" not in home_markup:
        errors.append("Inicio: falta el enlace de WER en DBLP")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    result = {"editions": len(catalog["editions"]), "papers": len(catalog["papers"]), "errors": errors, "warnings": warnings}
    (REPORTS_DIR / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = ["# Validación de WERpapers", "", f"- Ediciones: {result['editions']}", f"- Publicaciones: {result['papers']}", f"- Errores: {len(errors)}", f"- Advertencias: {len(warnings)}", ""]
    if errors:
        summary += ["## Errores", ""] + [f"- {item}" for item in errors] + [""]
    if warnings:
        summary += ["## Advertencias", ""] + [f"- {item}" for item in warnings] + [""]
    (REPORTS_DIR / "validation.md").write_text("\n".join(summary), encoding="utf-8")
    print(f"Validación: {len(errors)} errores, {len(warnings)} advertencias")
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
