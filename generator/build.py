from __future__ import annotations

import json
import hashlib
import re
import shutil
from datetime import date
from pathlib import Path
from urllib.parse import quote

from common import (
    REPORTS_DIR,
    SITE_DIR,
    absolute_puc,
    h,
    legacy_folder,
    load_catalog,
    paper_filename,
    paper_relative_url,
    pdf_filename,
    pdf_relative_url,
    split_pages,
)

THEME_DIR = Path(__file__).resolve().parents[1] / "theme"
EVENT_SITES_PATH = Path(__file__).resolve().parents[1] / "data" / "event-sites.json"
CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "catalog.json"


def asset_version() -> str:
    digest = hashlib.sha256()
    for path in (THEME_DIR / "styles.css", THEME_DIR / "i18n.js", THEME_DIR / "search.js", THEME_DIR / "logo-werpapers-restored.webp", CATALOG_PATH):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


ASSET_VERSION = asset_version()
COMMITTEE_KEYS = {
    "Program Committee": "committee.program",
    "Regular Research Track Committee": "committee.research",
    "Masters and Doctoral Track Committee": "committee.masters",
    "Software Requirements Tools Track Committee": "committee.tools",
    "Industry Track Committee": "committee.industry",
    "Tutorial Track Committee": "committee.tutorial",
    "Journal First Track Committee": "committee.journalFirst",
}


def shell(title: str, description: str, body: str, canonical: str, head_extra: str = "", depth: int = 0) -> str:
    prefix = "../" * depth
    local_root = prefix + "index.html"
    local_assets = prefix + "assets"
    local_history = prefix + "historia.html"
    local_anais = prefix + "anais.html"
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index,follow">
  <title>{h(title)}</title>
  <meta name="description" content="{h(description)}">
  <link rel="canonical" href="{h(canonical)}">
  <link rel="stylesheet" href="{h(local_assets + '/styles.css')}?v={ASSET_VERSION}">
{head_extra}</head>
<body>
  <a class="skip-link" href="#main">Saltar al contenido</a>
  <header class="site-header">
    <a class="brand" href="{h(local_root)}" aria-label="WERpapers"><img src="{h(local_assets + '/logo-werpapers-restored.webp')}?v={ASSET_VERSION}" width="1493" height="1054" alt="WERpapers"></a>
    <div class="header-tools">
      <nav aria-label="Principal"><a href="{h(local_root)}" data-i18n="nav.home">Inicio</a><a href="{h(local_anais)}" data-i18n="nav.anais">Anais</a><a href="{h(local_root)}#ediciones" data-i18n="nav.editions">Ediciones</a><a href="{h(local_history)}" data-i18n="nav.history">Historia</a><a href="{h(local_root)}#buscar" data-i18n="nav.search">Buscar</a></nav>
      <div class="language-switcher" role="group" aria-label="Idioma"><button type="button" data-lang="pt">PT</button><button type="button" data-lang="en">EN</button><button type="button" data-lang="es">ES</button></div>
    </div>
  </header>
  <main id="main">{body}</main>
  <footer><p>WERpapers · Workshop on Requirements Engineering · ISSN 2675-0066</p><p data-i18n="footer.description">Repositorio académico de acceso abierto mantenido como colección estática.</p><p><a href="https://dblp.org/db/conf/wer/index.html" target="_blank" rel="external noopener" data-i18n="footer.dblp">WER en DBLP</a></p></footer>
  <script src="{h(local_assets + '/i18n.js')}?v={ASSET_VERSION}" defer></script>
  <script src="{h(local_assets + '/search-index.js')}?v={ASSET_VERSION}" defer></script>
  <script src="{h(local_assets + '/search.js')}?v={ASSET_VERSION}" defer></script>
</body>
</html>
"""


def root_url(canonical: str) -> str:
    marker = "/WERpapers"
    return canonical.split(marker, 1)[0] + marker + "/"


def asset_url(canonical: str, asset: str) -> str:
    return root_url(canonical) + asset


def bibtex_for(paper: dict) -> str:
    if paper.get("bibtex"):
        return paper["bibtex"]
    authors = " and ".join(paper.get("authors", []))
    values = [
        f"@inproceedings{{{paper['id']},",
        f"  author = {{{authors}}},",
        f"  title = {{{paper['title']}}},",
        f"  booktitle = {{{paper.get('conference_title') or 'Workshop on Requirements Engineering (WER)'}}},",
        f"  year = {{{paper['year']}}},",
        f"  issn = {{{paper.get('issn') or '2675-0066'}}},",
    ]
    if paper.get("isbn"):
        values.append(f"  isbn = {{{paper['isbn']}}},")
    if paper.get("doi"):
        values.append(f"  doi = {{{paper['doi']}}},")
    values[-1] = values[-1].rstrip(",")
    values.append("}")
    return "\n".join(values)


def preface_title_attributes(paper: dict) -> str:
    title = paper.get("title", "")
    if re.search(r"(?i)^preface:\s*proceedings\s+of", title):
        number = paper["year"] - 1997
        return f' data-preface-title data-year="{h(paper["year"])}" data-number="{h(number)}"'
    return ""


def scholar_url(paper: dict) -> str:
    """Build a precise Scholar search without pretending it is a stable record URL."""
    return "https://scholar.google.com/scholar?q=" + quote(f'"{paper["title"]}"')


def paper_page(paper: dict) -> str:
    page_rel = paper_relative_url(paper)
    pdf_rel = pdf_relative_url(paper)
    canonical = absolute_puc(page_rel)
    pdf_url = absolute_puc(pdf_rel)
    authors = paper.get("authors", [])
    first_page, last_page = split_pages(paper.get("pages", ""))
    meta = [
        ("citation_title", paper["title"]),
        *(("citation_author", author) for author in authors),
        ("citation_publication_date", paper.get("publication_date") or str(paper["year"])),
        ("citation_conference_title", paper.get("conference_title") or "Workshop on Requirements Engineering (WER)"),
        ("citation_issn", paper.get("issn") or "2675-0066"),
        ("citation_isbn", paper.get("isbn", "")),
        ("citation_doi", paper.get("doi", "")),
        ("citation_abstract", paper.get("abstract", "")),
        ("citation_firstpage", first_page),
        ("citation_lastpage", last_page),
        ("citation_pdf_url", pdf_url),
    ]
    meta_html = "\n".join(f'  <meta name="{h(name)}" content="{h(value)}">' for name, value in meta if value)
    json_ld = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": paper["title"],
        "description": paper.get("abstract", ""),
        "author": [{"@type": "Person", "name": author} for author in authors],
        "datePublished": paper.get("publication_date") or str(paper["year"]),
        "isPartOf": {"@type": "PublicationEvent", "name": paper.get("conference_title") or "Workshop on Requirements Engineering (WER)"},
        "identifier": paper.get("doi") or paper["id"],
        "url": canonical,
        "encoding": {"@type": "MediaObject", "contentUrl": pdf_url, "encodingFormat": "application/pdf"},
    }
    head_extra = meta_html + "\n  <script type=\"application/ld+json\">" + json.dumps(json_ld, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    author_html = "; ".join(h(author) for author in authors)
    details = [
        f"<span data-conference-title>{h(paper.get('conference_title') or 'Workshop on Requirements Engineering (WER)')}</span>",
        f"<span>{h(paper['year'])}</span>",
    ]
    if paper.get("doi"):
        details.append(f'<a href="https://doi.org/{h(paper["doi"])}">DOI {h(paper["doi"])}</a>')
    section = paper.get("section", "")
    if section.lower() == "preface":
        section_html = '<span data-i18n="paper.preface">Prefacio</span>'
    else:
        section_html = h(section) if section else '<span data-i18n="paper.article">Artículo</span>'
    body = f"""
<article class="paper">
  <p class="eyebrow">{section_html} · WER{h(paper['year'])}</p>
  <h1 class="citation_title"{preface_title_attributes(paper)}>{h(paper['title'])}</h1>
  <p class="authors citation_author">{author_html}</p>
  <div class="paper-meta">{''.join(details)}</div>
  <p class="actions"><a class="button" href="{h(pdf_url)}" data-i18n="paper.readPdf">Leer PDF</a><a class="button secondary" href="index.html" data-i18n="paper.viewEdition">Ver edición</a><a class="button secondary" href="{h(scholar_url(paper))}" target="_blank" rel="noopener" data-i18n="paper.scholar">Google Scholar</a></p>
  <section aria-labelledby="abstract-heading"><h2 id="abstract-heading" data-i18n="paper.abstract">Resumen</h2><p class="abstract">{h(paper.get('abstract') or 'Resumen no disponible.')}</p></section>
  {f'<section><h2 data-i18n="paper.keywords">Palabras clave</h2><p>{h(paper.get("keywords"))}</p></section>' if paper.get('keywords') else ''}
  <details><summary data-i18n="paper.cite">Cómo citar</summary><pre><code>{h(bibtex_for(paper))}</code></pre></details>
</article>"""
    return shell(paper["title"], paper.get("abstract") or paper["title"], body, canonical, head_extra, depth=2)


def edition_page(edition: dict, papers: list[dict]) -> str:
    rel = f'{legacy_folder(edition["year"])}/index.html'
    canonical = absolute_puc(rel)
    items = "\n".join(
        f'<li><a href="{h(paper_filename(paper))}"{preface_title_attributes(paper)}>{h(paper["title"])}</a><span>{h("; ".join(paper.get("authors", [])))}</span></li>'
        for paper in papers
    )
    metadata = [
        ("edition.locationDate", "Lugar y fecha", edition.get("location_and_date", "")),
        ("edition.editors", "Editores", edition.get("editors", "")),
        ("edition.publisher", "Editorial", edition.get("publisher", "")),
        ("edition.isbn", "ISBN", edition.get("isbn", "")),
        ("edition.issn", "ISSN", edition.get("issn", "")),
    ]
    metadata_classes = {"edition.locationDate": "location", "edition.editors": "editors"}
    metadata_parts = []
    for key, label, value in metadata:
        if not value:
            continue
        rendered_value = h(value)
        if key == "edition.locationDate":
            location, localized_date, days, month, event_year = format_location_and_date(value)
            if days:
                rendered_value = f'<span class="event-location" data-location="{h(location)}">{h(location)}</span> · <time class="event-date" data-days="{h(days)}" data-month="{h(month)}" data-year="{h(event_year)}">{h(localized_date)}</time>'
        metadata_parts.append(f'<div class="{h(metadata_classes.get(key, "compact"))}"><dt data-i18n="{h(key)}">{h(label)}</dt><dd>{rendered_value}</dd></div>')
    metadata_html = "".join(metadata_parts)
    contact_link = f'<a href="mailto:{h(edition.get("contact_email", ""))}" data-i18n="edition.contact">Contacto</a>' if edition.get("contact_email") else ""
    edition_actions = f'<nav class="edition-actions" aria-label="Edición"><a href="expediente.html" data-i18n="edition.masthead">Expediente</a>{contact_link}</nav>'
    body = f"""
<section class="hero compact edition-hero"><p class="eyebrow"><span data-i18n="edition.label">Edición</span> {h(edition['year'])}</p><h1>WER{h(edition['year'])}</h1><p class="edition-title" data-edition-title data-year="{h(edition['year'])}" data-number="{h(edition.get('edition_number') or edition['year'] - 1997)}">WER{h(edition['year'])}: Actas del {h(edition.get('edition_number') or edition['year'] - 1997)}.º Workshop en Ingeniería de Requerimientos</p>{edition_actions}<div class="edition-bibliography" aria-labelledby="edition-bibliography-title"><h2 id="edition-bibliography-title" data-i18n="edition.metadata">Datos bibliográficos de la edición</h2><dl>{metadata_html}</dl></div></section>
<section class="content"><div class="section-heading"><h2 data-i18n="edition.publications">Publicaciones</h2><span>{len(papers)} <span data-i18n="edition.documents">documentos</span></span></div><ol class="paper-list">{items}</ol></section>"""
    return shell(f"WER{edition['year']} · WERpapers", edition.get("title") or "Publicaciones WER", body, canonical, depth=2)


def masthead_page(edition: dict, papers: list[dict]) -> str:
    canonical = absolute_puc(f'{legacy_folder(edition["year"])}/expediente.html')
    editors = [editor.strip() for editor in edition.get("editors", "").split(";") if editor.strip()]
    editors_html = "".join(f"<li>{h(editor)}</li>" for editor in editors)
    committee_sections = []
    for committee in edition.get("committees", []):
        key = COMMITTEE_KEYS.get(committee.get("name", ""), "")
        heading = f'<h2 data-i18n="{h(key)}">{h(committee["name"])}</h2>' if key else f'<h2>{h(committee.get("name", ""))}</h2>'
        members = "".join(f'<li>{h(member)}</li>' for member in committee.get("members", []))
        committee_sections.append(f'<section class="committee-section">{heading}<ul class="committee-list">{members}</ul></section>')
    administrative_papers = [
        paper for paper in papers
        if re.search(r"(?i)prefac|^organization$|^introdu(?:ction|ção)$", paper.get("title", "").strip())
    ]
    documents_html = ""
    if administrative_papers:
        links = "".join(f'<li><a href="{h(paper_filename(paper))}"{preface_title_attributes(paper)}>{h(paper["title"])}</a></li>' for paper in administrative_papers)
        documents_html = f'<section class="committee-section"><h2 data-i18n="masthead.documents">Documentos de organización y prefacio</h2><ul>{links}</ul></section>'
    contact_html = f'<a class="button secondary" href="mailto:{h(edition.get("contact_email", ""))}" data-i18n="edition.contact">Contacto</a>' if edition.get("contact_email") else ""
    body = f"""
<section class="hero compact"><p class="eyebrow"><span data-i18n="edition.label">Edición</span> {h(edition['year'])}</p><h1><span data-i18n="masthead.title">Expediente</span> · WER{h(edition['year'])}</h1><p data-i18n="masthead.description">Equipo editorial y comités registrados para esta edición.</p><p class="actions"><a class="button" href="index.html" data-i18n="masthead.back">Volver a las publicaciones</a>{contact_html}</p></section>
<section class="content masthead-content"><section class="committee-section"><h2 data-i18n="masthead.editors">Editores de los proceedings</h2><ul class="committee-list editors-list">{editors_html}</ul></section>{''.join(committee_sections)}{documents_html}</section>"""
    return shell(f"Expediente · WER{edition['year']}", f"Equipo editorial y comités de WER{edition['year']}", body, canonical, depth=2)


def home_page(editions: list[dict], papers: list[dict]) -> str:
    canonical = absolute_puc("index.html")
    edition_cards = "\n".join(
        f'<li><a href="{h(legacy_folder(e["year"]))}/index.html"><strong>WER{h(e["year"])}</strong><span>{len(e.get("paper_ids", []))} <span data-i18n="stats.publications">publicaciones</span></span></a></li>'
        for e in sorted(editions, key=lambda item: item["year"], reverse=True)
    )
    body = f"""
<section class="hero home-hero">
  <p class="eyebrow">WER · 1998–{max(e['year'] for e in editions)}</p>
  <div class="hero-title-group"><h1 data-i18n="home.title">Workshop en Ingeniería de Requerimientos</h1></div>
  <p class="institutional-intro" data-i18n="home.description">Este Workshop se viene realizando desde 1998 y tiene como principal objetivo la consolidación de una comunidad Iberoamericana de investigación en Ingeniería de Requisitos.</p>
  <div class="stats"><span><strong>{len(editions)}</strong> <span data-i18n="stats.editions">ediciones</span></span><span><strong>{len(papers)}</strong> <span data-i18n="stats.publications">publicaciones</span></span><span><strong>3</strong> <span data-i18n="stats.languages">idiomas</span></span></div>
</section>
<section id="buscar" class="search-panel"><label for="search"><span data-i18n="search.label">Buscar en WERpapers</span><input id="search" type="search" placeholder="Título, autor, año, palabra clave o resumen" data-i18n-placeholder="search.placeholder" autocomplete="off"></label><p id="search-status" aria-live="polite"></p><ul id="search-results" class="search-results"></ul></section>
<section id="ediciones" class="content"><div class="section-heading"><h2 data-i18n="home.explore">Explorar por edición</h2><span>1998–{max(e['year'] for e in editions)}</span></div><ul class="edition-grid">{edition_cards}</ul></section>
<section class="history-callout"><p class="eyebrow" data-i18n="home.memory">Memoria de WER</p><h2 data-i18n="home.historyTitle">Los sitios de cada edición, preservados</h2><p data-i18n="home.historyDescription">Consulta las páginas oficiales y las copias archivadas de cada Workshop, desde WER1998 hasta la edición actual.</p><a class="button" href="historia.html" data-i18n="home.historyButton">Ver historia de las ediciones</a></section>"""
    return shell("WERpapers · Open Access Repository", "Repositorio de las publicaciones del Workshop on Requirements Engineering", body, canonical)


def anais_page(editions: list[dict]) -> str:
    canonical = absolute_puc("anais.html")
    edition_links = "".join(
        f'<li><a href="{h(legacy_folder(edition["year"]))}/index.html"><strong>WER{h(edition["year"])}</strong><span class="event-location" data-location="{h(format_location_and_date(edition.get("location_and_date", ""))[0])}">{h(format_location_and_date(edition.get("location_and_date", ""))[0])}</span></a></li>'
        for edition in sorted(editions, key=lambda item: item["year"], reverse=True)
    )
    periodical_json = {
        "@context": "https://schema.org",
        "@type": "Periodical",
        "name": "Anais do Workshop em Engenharia de Requisitos",
        "alternateName": ["Actas del Workshop en Ingeniería de Requerimientos", "Proceedings of the Workshop on Requirements Engineering"],
        "issn": "2675-0066",
        "url": canonical,
        "inLanguage": ["pt", "es", "en"],
        "sameAs": "https://portal.issn.org/resource/ISSN/2675-0066",
    }
    head_extra = '  <meta name="DC.identifier" content="ISSN 2675-0066">\n  <meta name="DC.type" content="Text.Serial">\n  <script type="application/ld+json">' + json.dumps(periodical_json, ensure_ascii=False).replace("</", "<\\/") + "</script>\n"
    body = f"""
<section class="hero compact anais-hero"><p class="eyebrow">ISSN 2675-0066</p><h1 data-i18n="anais.title">Actas del Workshop en Ingeniería de Requerimientos</h1><p data-i18n="anais.subtitle">Serie editorial de acceso abierto del WER.</p><nav class="anais-nav" aria-label="Anais"><a href="#presentacion" data-i18n="anais.presentation">Presentación</a><a href="#normas" data-i18n="anais.guidelines">Normas</a><a href="#expediente" data-i18n="anais.masthead">Expediente</a><a href="#ediciones" data-i18n="anais.editions">Ediciones</a><a href="#contacto" data-i18n="anais.contact">Contacto</a></nav></section>
<section id="presentacion" class="content anais-section"><p class="eyebrow" data-i18n="anais.presentation">Presentación</p><h2 data-i18n="anais.identityTitle">Identidad editorial de WERpapers</h2><p data-i18n="anais.presentation1">WERpapers es la publicación seriada de acceso abierto que reúne las actas del Workshop en Ingeniería de Requerimientos, celebrado anualmente desde 1998.</p><p data-i18n="anais.presentation2">Su misión es preservar y difundir investigación, educación y experiencias de industria en Ingeniería de Requerimientos para la comunidad iberoamericana, en portugués, español e inglés.</p><p data-i18n="anais.presentation3">La serie posee el ISSN 2675-0066, registrado por Editora PUC-Rio. La colección histórica se conserva en PUC-Rio y cuenta con un espejo mantenido en UFRN.</p><dl class="serial-facts"><div><dt>ISSN</dt><dd><a href="https://portal.issn.org/resource/ISSN/2675-0066">2675-0066</a></dd></div><div><dt data-i18n="anais.periodicity">Periodicidad</dt><dd data-i18n="anais.annual">Anual</dd></div><div><dt data-i18n="anais.languages">Idiomas</dt><dd data-i18n="anais.languageValues">Portugués, español e inglés</dd></div><div><dt data-i18n="anais.access">Acceso</dt><dd data-i18n="anais.openAccess">Acceso abierto</dd></div></dl></section>
<section id="normas" class="content anais-section"><p class="eyebrow" data-i18n="anais.guidelines">Normas</p><h2 data-i18n="anais.guidelinesTitle">Normas editoriales y de publicación</h2><p data-i18n="anais.guidelinesIntro">Cada convocatoria puede definir modalidades y límites específicos, pero toda publicación de WER sigue estos principios comunes.</p><div class="policy-grid">
<section><h3 data-i18n="anais.submissionTitle">Envío y selección</h3><ul><li data-i18n="anais.submission1">Se aceptan contribuciones originales de investigación, educación o industria sobre cualquier aspecto de Ingeniería de Requerimientos.</li><li data-i18n="anais.submission2">Los trabajos pueden presentarse en portugués, español o inglés, en PDF y según el formato indicado por la convocatoria.</li><li data-i18n="anais.submission3">Cada trabajo es evaluado por al menos tres integrantes del comité, considerando relevancia, solidez, originalidad, claridad y calidad del lenguaje.</li></ul></section>
<section><h3 data-i18n="anais.ethicsTitle">Ética y autoría</h3><ul><li data-i18n="anais.ethics1">El manuscrito debe ser original, no estar publicado previamente ni sometido simultáneamente en otro lugar.</li><li data-i18n="anais.ethics2">Todas las personas autoras deben haber contribuido significativamente y declarar fuentes y conflictos de interés.</li><li data-i18n="anais.ethics3">El plagio, la falsificación de datos y cualquier otra mala práctica editorial son inadmisibles.</li></ul></section>
<section><h3 data-i18n="anais.editorsTitle">Responsabilidad editorial</h3><ul><li data-i18n="anais.editors1">Los editores deciden con imparcialidad, protegen el anonimato de la revisión y preservan la integridad del registro académico.</li><li data-i18n="anais.editors2">Deben corregir errores, publicar fe de erratas y actuar ante evidencia de conducta indebida.</li></ul></section>
<section><h3 data-i18n="anais.reviewersTitle">Responsabilidad de revisión</h3><ul><li data-i18n="anais.reviewers1">Las evaluaciones son confidenciales, objetivas y sustentadas con argumentos claros.</li><li data-i18n="anais.reviewers2">Quien tenga un conflicto de interés no debe participar en la evaluación.</li></ul></section>
<section><h3 data-i18n="anais.rightsTitle">Derechos y licencia</h3><ul><li data-i18n="anais.rights1">Las personas autoras conservan sus derechos y publican en acceso abierto bajo licencia Creative Commons Atribución 4.0 Internacional.</li><li data-i18n="anais.rights2">Pueden depositar la versión publicada en páginas personales y repositorios institucionales.</li></ul></section>
<section><h3 data-i18n="anais.feesTitle">Costos y permanencia</h3><ul><li data-i18n="anais.fees1">WERpapers no cobra cargos de publicación ni APC.</li><li data-i18n="anais.fees2">Las comunicaciones sobre correcciones deben dirigirse a los editores de la edición correspondiente.</li></ul></section>
</div><p><a href="https://publicationethics.org/" data-i18n="anais.cope">Código y recursos de COPE</a></p></section>
<section id="expediente" class="content anais-section"><p class="eyebrow" data-i18n="anais.masthead">Expediente</p><h2 data-i18n="anais.generalMasthead">Expediente general de WERpapers</h2><div class="identity-grid"><section><h3 data-i18n="anais.editorChief">Editor jefe</h3><p>Julio C. S. P. Leite · Universidade Federal da Bahia, Brasil</p></section><section><h3 data-i18n="anais.publicationResponsibles">Responsables de publicación</h3><p>Roxana Portugal · Universidad Nacional de San Antonio Abad del Cusco, Perú</p><p>Lyrene Silva · Universidade Federal do Rio Grande do Norte, Brasil</p></section></div><p data-i18n="anais.mastheadDescription">Cada edición designa editores responsables del programa científico y de sus actas. Desde 2021 también participan responsables por línea; la organización local gestiona la logística de cada evento. Los expedientes anuales detallan esos equipos y sus comités.</p></section>
<section id="ediciones" class="content anais-section"><p class="eyebrow" data-i18n="anais.editions">Ediciones</p><h2 data-i18n="anais.editionsTitle">Actas publicadas</h2><ul class="edition-grid anais-edition-grid">{edition_links}</ul></section>
<section id="contacto" class="content anais-section"><p class="eyebrow" data-i18n="anais.contact">Contacto</p><h2 data-i18n="anais.contactTitle">Contacto de WERpapers</h2><p>Lyrene Silva · Departamento de Informática e Matemática Aplicada, UFRN · Natal/RN, Brasil</p><p><a href="mailto:papers.wer@gmail.com">papers.wer@gmail.com</a> · <a href="mailto:lyrene.silva@ufrn.br">lyrene.silva@ufrn.br</a> · +55 84 3342-2225</p></section>"""
    return shell("Anais · WERpapers", "Serie editorial de acceso abierto del Workshop en Ingeniería de Requerimientos · ISSN 2675-0066", body, canonical, head_extra)


def history_page(editions: list[dict], event_sites: dict[str, str]) -> str:
    canonical = absolute_puc("historia.html")
    rows = []
    for edition in sorted(editions, key=lambda item: item["year"], reverse=True):
        year = str(edition["year"])
        event_url = event_sites.get(year, "")
        archive_key = "history.archive" if "web.archive.org" in event_url else "history.site"
        archive_label = "Copia archivada" if "web.archive.org" in event_url else "Sitio de la edición"
        event_link = f'<a href="{h(event_url)}" target="_blank" rel="noopener" data-i18n="{archive_key}">{archive_label}</a>' if event_url else '<span data-i18n="history.unavailable">No disponible</span>'
        edition_number = edition.get("edition_number") or int(year) - 1997
        location, event_date, days, month, event_year = format_location_and_date(edition.get("location_and_date", ""))
        context = f'<span class="edition-context"><strong class="edition-number" data-number="{h(edition_number)}">{h(edition_number)}.ª edición</strong><span class="event-location" data-location="{h(location)}">{h(location)}</span><time class="event-date" data-days="{h(days)}" data-month="{h(month)}" data-year="{h(event_year)}">{h(event_date)}</time></span>'
        rows.append(f'<li><strong>WER{h(year)}</strong>{context}<div><a href="{h(legacy_folder(year))}/index.html" data-i18n="history.publications">Publicaciones</a>{event_link}</div></li>')
    body = f"""
<section class="hero compact"><p class="eyebrow" data-i18n="history.eyebrow">Archivo histórico</p><h1 data-i18n="history.title">Historia de las ediciones</h1><p data-i18n="history.description">Directorio de los sitios que acompañaron cada edición de WER. Cuando el sitio original desapareció, se conserva el mejor enlace disponible en Internet Archive.</p></section>
<section class="content"><ul class="history-list">{''.join(rows)}</ul></section>"""
    return shell("Historia de las ediciones · WERpapers", "Archivo de los sitios web de cada edición de WER", body, canonical)


def format_location_and_date(value: str) -> tuple[str, str, str, str, str]:
    match = re.match(r"^(.*),\s*(\d{1,2}(?:-\d{1,2})?)\s+([A-Za-z]+)\s+(\d{4})$", value.strip())
    if not match:
        return value, "", "", "", ""
    location, days, month, year = match.groups()
    months = {
        "january": "enero", "february": "febrero", "march": "marzo", "april": "abril",
        "may": "mayo", "june": "junio", "july": "julio", "august": "agosto",
        "september": "septiembre", "october": "octubre", "octuber": "octubre",
        "november": "noviembre", "december": "diciembre",
    }
    days = days.replace("-", "–")
    normalized_month = month.lower()
    return location, f"{days} de {months.get(normalized_month, normalized_month)} de {year}", days, normalized_month, year


def main() -> None:
    catalog = load_catalog()
    event_sites = json.loads(EVENT_SITES_PATH.read_text(encoding="utf-8"))
    if SITE_DIR.exists():
        for _ in range(3):
            shutil.rmtree(SITE_DIR, ignore_errors=True)
            if not SITE_DIR.exists():
                break
            for debris in SITE_DIR.rglob(".DS_Store"):
                debris.unlink(missing_ok=True)
        if SITE_DIR.exists():
            raise RuntimeError(f"No se pudo limpiar el directorio generado: {SITE_DIR}")
    SITE_DIR.mkdir(parents=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copytree(THEME_DIR, SITE_DIR / "assets")

    paper_by_id = {paper["id"]: paper for paper in catalog["papers"]}
    for paper in catalog["papers"]:
        destination = SITE_DIR / paper_relative_url(paper)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(paper_page(paper), encoding="utf-8")

    for edition in catalog["editions"]:
        edition_papers = [paper_by_id[paper_id] for paper_id in edition.get("paper_ids", []) if paper_id in paper_by_id]
        destination = SITE_DIR / legacy_folder(edition["year"]) / "index.html"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(edition_page(edition, edition_papers), encoding="utf-8")
        (destination.parent / "expediente.html").write_text(masthead_page(edition, edition_papers), encoding="utf-8")

    (SITE_DIR / "index.html").write_text(home_page(catalog["editions"], catalog["papers"]), encoding="utf-8")
    (SITE_DIR / "anais.html").write_text(anais_page(catalog["editions"]), encoding="utf-8")
    (SITE_DIR / "historia.html").write_text(history_page(catalog["editions"], event_sites), encoding="utf-8")
    search_items = [{"title": p["title"], "authors": p.get("authors", []), "year": p["year"], "keywords": p.get("keywords", ""), "abstract": p.get("abstract", ""), "url": paper_relative_url(p)} for p in catalog["papers"]]
    (SITE_DIR / "assets" / "search-index.js").write_text("window.WER_SEARCH_INDEX = " + json.dumps(search_items, ensure_ascii=False) + ";\n", encoding="utf-8")

    sitemap_urls = [absolute_puc("index.html"), absolute_puc("anais.html"), absolute_puc("historia.html")]
    sitemap_urls += [absolute_puc(f'{legacy_folder(e["year"])}/index.html') for e in catalog["editions"]]
    sitemap_urls += [absolute_puc(f'{legacy_folder(e["year"])}/expediente.html') for e in catalog["editions"]]
    sitemap_urls += [absolute_puc(paper_relative_url(p)) for p in catalog["papers"]]
    sitemap_urls += [absolute_puc(pdf_relative_url(p)) for p in catalog["papers"]]
    today = date.today().isoformat()
    sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(f'  <url><loc>{h(url)}</loc><lastmod>{today}</lastmod></url>' for url in sitemap_urls) + "\n</urlset>\n"
    (SITE_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (SITE_DIR / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {absolute_puc('sitemap.xml')}\n", encoding="utf-8")
    robot_links = "\n".join(f'<li><a href="{h(paper_relative_url(p))}">{h(p["title"])}</a></li>' for p in catalog["papers"])
    (SITE_DIR / "index-for-robots.html").write_text(shell("Índice completo de WERpapers", "Listado de todas las publicaciones", f'<section class="content"><h1>Índice completo</h1><ul class="paper-list">{robot_links}</ul></section>', absolute_puc("index-for-robots.html")), encoding="utf-8")

    manifest_lines = ["year,paper_id,relative_pdf_path,puc_public_pdf_url,source_pdf_url"]
    manifest_lines += [f'{p["year"]},{p["id"]},"{pdf_relative_url(p)}","{absolute_puc(pdf_relative_url(p))}","{p["source_pdf_url"]}"' for p in catalog["papers"]]
    (REPORTS_DIR / "pdf-manifest.csv").write_text("\n".join(manifest_lines) + "\n", encoding="utf-8")
    print(f"Sitio generado: {len(catalog['editions'])} ediciones, {len(catalog['papers'])} publicaciones")


if __name__ == "__main__":
    main()
