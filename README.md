# WERpapers Static

Nueva versión estática de WERpapers para PUC-Rio.

Vista previa para revisión de los co-chairs:
<https://sites-re-puc-rio.github.io/new-werpapers/>

El sitio publicado no requiere Lua, PHP, WordPress, base de datos ni un
generador instalado en el servidor. La carpeta `site/` contiene únicamente
HTML, CSS, JavaScript, XML, texto e imágenes. Los PDFs conservan sus rutas
históricas bajo `artigos/artigos_WERxx/`.

## Estructura

- `data/catalog.json`: catálogo bibliográfico normalizado.
- `generator/import_ufrn.py`: importa la versión plana mantenida en UFRN.
- `generator/build.py`: genera el sitio estático completo.
- `generator/validate.py`: valida requisitos de Google Scholar y rutas.
- `site/`: salida lista para publicar.
- `reports/`: informes de validación y manifiesto de PDFs.

## Flujo local

```bash
python3 generator/import_ufrn.py \
  --editions-dir /ruta/a/werpapersnapucrio \
  --fetch-pages

python3 generator/build.py
python3 generator/validate.py
```

La importación remota solo se necesita para actualizar abstracts y metadatos
desde UFRN. La construcción y validación posteriores funcionan sin red.

## Publicación

Copiar el contenido de `site/` sobre el directorio público `WERpapers/` sin
eliminar los PDFs históricos existentes. El archivo
`reports/pdf-manifest.csv` enumera la ruta exacta que debe conservar cada PDF y su URL pública fija bajo `http://wer.inf.puc-rio.br/WERpapers/`. Estas URL HTTP son deliberadas: corresponden a las direcciones históricas ya citadas e indexadas. El centro de cómputo puede ofrecer también HTTPS, pero no debe retirar ni cambiar las URL HTTP sin una redirección individual permanente.

Para una edición nueva, se importan o ingresan sus datos localmente, se ejecuta
la construcción y se entrega nuevamente la carpeta `site/` al centro de
cómputo.

## Vista previa en GitHub

Cada actualización de la rama `main` reconstruye, valida y publica
automáticamente `site/` mediante GitHub Pages. La vista previa conserva en sus
metadatos y botones de PDF las URL definitivas de PUC-Rio; GitHub Pages se usa
solamente para evaluación y no debe convertirse en la dirección canónica del
repositorio académico.
