# pdftotext API

A minimal REST API for extracting the existing text layer from digital PDF
documents with the `pdftotext` command-line utility from
[Poppler](https://poppler.freedesktop.org/).

This repository reconstructs one of the document-ingestion components used in
the former ProWatsom backend. It contains no customer documents, credentials,
or proprietary business rules.

## Important distinction

`pdftotext` is **not OCR**. It reads text already embedded in a PDF. It is fast,
local, deterministic, and inexpensive, but it cannot recognize text inside a
scanned image. A scanned PDF requires an OCR engine such as Tesseract or
EasyOCR.

## What it demonstrates

- Native PDF text extraction with Poppler.
- Page separation using PDF form-feed markers.
- Layout-preserving extraction with `-layout`.
- UTF-8 output.
- Detection of PDFs without a usable text layer.
- FastAPI, Docker, automated tests, and GitHub Actions.

## Run with Docker

```bash
docker build -t pdftotext-api .
docker run --rm -p 8000:8000 pdftotext-api
```

Open `http://localhost:8000/docs`.

## Run locally

Ubuntu/Debian:

```bash
sudo apt-get update
sudo apt-get install poppler-utils
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn main:app --reload
```

## Extract text

```bash
curl -X POST "http://localhost:8000/extract" \
  -F "file=@document.pdf"
```

Example response:

```json
{
  "engine": "pdftotext",
  "filename": "document.pdf",
  "text": "Text already stored in the PDF...",
  "page_count": 2,
  "character_count": 1840,
  "has_text_layer": true,
  "duration_ms": 42,
  "pages": [
    {"page": 1, "text": "First page text..."},
    {"page": 2, "text": "Second page text..."}
  ]
}
```

## Direct command

The API executes the equivalent of:

```bash
pdftotext -layout -enc UTF-8 document.pdf -
```

The final `-` sends the extracted text to standard output.

## Tests

```bash
pytest -q
```

## License

MIT © 2026 George Hamilton Buzzi Polesel.
