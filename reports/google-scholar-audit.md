# Auditoría de preparación para Google Scholar

Fecha: 22 de julio de 2026

## Conclusión

La nueva versión está sustancialmente mejor preparada para Google Scholar que el sitio anterior. La estructura HTML cumple los requisitos técnicos principales de Scholar: una URL independiente por publicación, metadatos bibliográficos legibles por robots, resumen visible, enlace directo al PDF y navegación mediante enlaces HTML simples.

Esto aumenta la probabilidad de indexación, pero no la garantiza. Antes de publicar existen bloqueos relacionados con los archivos PDF y con la configuración pública del servidor de la PUC-Rio. Las URL canónicas y de PDF utilizan deliberadamente el origen histórico `http://wer.inf.puc-rio.br/WERpapers/` para conservar las direcciones ya citadas e indexadas.

Referencia oficial: [Google Scholar — Inclusion Guidelines for Webmasters](https://scholar.google.com/intl/en/scholar/inclusion.html).

## Lo que ya cumple la versión estática

- 592 páginas HTML individuales, una por publicación.
- 592 títulos, autores, fechas, resúmenes y URL de PDF presentes.
- Metadatos Highwire `citation_title`, `citation_author`, `citation_publication_date`, `citation_conference_title`, `citation_issn`, `citation_pdf_url` y, cuando existen, ISBN y DOI.
- URL canónica y datos estructurados `ScholarlyArticle` en cada publicación.
- Resumen completo visible sin inicio de sesión ni interacción especial.
- PDF enlazado directamente y situado en el mismo directorio de su página HTML.
- Navegación con enlaces HTML: portada → edición → publicación → PDF.
- `robots.txt` permite el rastreo y declara el sitemap.
- `sitemap.xml` incluye 1.245 URL, entre ellas las 592 páginas y los 592 PDF.
- Todos los nombres de archivo PDF usan caracteres seguros para una URL.
- 207 DOI válidos y únicos; 522 registros con ISBN; 429 con palabras clave.

## Bloqueos antes de publicar

### Prioridad crítica

1. **Incorporar físicamente los PDF.** El directorio generado `site/` contiene el sitio, pero no todavía las 592 copias finales de los PDF. Deben copiarse a las rutas históricas exactas antes de entregar el paquete de producción.

2. **Corregir dos PDF inexistentes en el espejo UFRN.** Ambos responden HTTP 404:
   - `wer201400_2`, *Table of Contents*: `papers/WER2014/table.pdf`.
   - `wer202100_2`, *Tutorial - Analysis of business processes compliance with LGPD*: `papers/WER2021/WER_2021_paper_53.pdf`.

3. **Asegurar UTF-8 en la respuesta HTTP.** El servidor antiguo declara ISO-8859-1. El nuevo sitio debe responder `Content-Type: text/html; charset=UTF-8`; de lo contrario, títulos y resúmenes con acentos pueden llegar dañados a Scholar.

4. **Acceso público estable.** Las páginas y PDF deben devolver HTTP 200 sin autenticación, cortafuegos, CAPTCHA, cookies obligatorias ni restricciones geográficas para Googlebot y usuarios normales.

5. **Conservar las URL HTTP históricas.** La universidad puede corregir el certificado y ofrecer también HTTPS, lo cual es recomendable, pero no debe retirar las direcciones HTTP ya indexadas. Si decide redirigirlas, cada URL HTTP debe responder con un 301 hacia exactamente el mismo artículo o PDF en HTTPS, nunca hacia la portada.

### Prioridad alta

6. **Reducir cuatro PDF por debajo de 5 MiB**, límite indicado por Google Scholar, conservando texto seleccionable y la misma URL:
   - `wer200914`: 8,95 MiB.
   - `wer202305`: 7,73 MiB.
   - `wer201611`: 7,01 MiB.
   - `wer202403`: 5,99 MiB.

7. **Reexportar u obtener una copia con OCR de `wer201819`.** Su primera página no proporciona texto extraíble. El PDF debe conservar su apariencia, pero contener título, autores y cuerpo como texto buscable.

8. **Revisar manualmente 15 artículos cuyo título extraído del PDF coincide poco con el catálogo.** Puede deberse a codificación interna del PDF, orden de extracción o metadatos distintos; no todos son necesariamente defectuosos. La lista exacta está en `pdf-content-audit.json`.

9. **Mantener idénticos los datos en ambos espejos.** Título, autores, año, DOI y, preferiblemente, el archivo PDF deben coincidir en PUC-Rio y UFRN para facilitar que Scholar agrupe ambas fuentes como versiones del mismo trabajo.

## Mejoras que sí pueden hacerse en esta versión

1. **Corregir nueve resúmenes con problemas de codificación** (`&eacute`, `Ã§`, `sÃ£o`, etc.): `wer201214`, `wer201304`, `wer201305`, `wer201309`, `wer201310`, `wer201312`, `wer201610`, `wer202017` y `wer202100_2`.

2. **Agregar páginas inicial y final.** Ninguno de los 592 registros tiene todavía `citation_firstpage`/`citation_lastpage`. Scholar puede indexar sin ellas, pero son valiosas para identificar y consolidar correctamente las citas.

3. **Hacer específico el nombre del evento por edición.** Actualmente todas las páginas usan el genérico “Workshop on Requirements Engineering (WER)”. Conviene usar, por ejemplo, “29th Workshop on Requirements Engineering (WER 2026)”.

4. **Excluir de Scholar documentos puramente administrativos.** Las páginas tituladas *Organization* y *Table of Contents* no son artículos académicos y varias repiten exactamente el mismo título. Conviene mantenerlas accesibles para el lector, pero sin metadatos de artículo y con `noindex`.

5. **Dar mayor proximidad visual al resumen.** El resumen ya es visible y rastreable, pero en algunos artículos queda debajo de un título muy grande y de los botones. Reducir el encabezado o colocar el resumen antes de las acciones facilitaría la lectura y haría más evidente el contenido académico.

6. **Usar fechas `lastmod` reales en el sitemap o eliminarlas.** En cada reconstrucción todas las URL reciben la fecha del día aunque el documento histórico no haya cambiado. No es un requisito de Scholar, pero evita señales innecesarias de actualización masiva.

## Comprobaciones posteriores a la publicación

- Registrar el sitio y enviar `sitemap.xml` mediante Google Search Console.
- Probar que una muestra de páginas y PDF devuelve HTTP 200 y el tipo de contenido correcto desde una red externa.
- Buscar periódicamente títulos completos entre comillas en Google Scholar.
- No cambiar las URL históricas. Si alguna ruta tuviera que cambiar, usar una redirección HTTP 301 hacia la publicación equivalente, nunca hacia la portada.
- Tener paciencia con las actualizaciones: Google indica que los cambios de artículos ya indexados pueden tardar entre seis y nueve meses.

## Informes técnicos relacionados

- `remote-pdf-audit.md`: disponibilidad y peso de los 592 PDF del espejo UFRN.
- `remote-pdf-audit.json`: resultados completos de las respuestas HTTP.
- `pdf-content-audit.json`: análisis heurístico de texto extraíble, título, autores y referencias.
