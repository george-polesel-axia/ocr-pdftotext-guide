"""Minimal REST API for native PDF text extraction with Poppler pdftotext."""

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
COMMAND_TIMEOUT_SECONDS = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "60"))


class PageResult(BaseModel):
    page: int = Field(ge=1)
    text: str


class ExtractionResponse(BaseModel):
    engine: str = "pdftotext"
    filename: str
    text: str
    page_count: int
    character_count: int
    has_text_layer: bool
    duration_ms: int
    pages: list[PageResult]


app = FastAPI(
    title="pdftotext API",
    version="1.0.0",
    description="Native PDF text extraction using the pdftotext utility from Poppler.",
)


def split_pages(text: str) -> list[str]:
    pages = text.split("\f")
    while pages and not pages[-1].strip():
        pages.pop()
    return [page.strip() for page in pages] or [""]


def run_pdftotext(content: bytes) -> list[str]:
    if not shutil.which("pdftotext"):
        raise RuntimeError("pdftotext is not installed")

    with tempfile.NamedTemporaryFile(prefix="pdftotext-", suffix=".pdf") as temporary:
        temporary.write(content)
        temporary.flush()
        try:
            result = subprocess.run(
                [
                    "pdftotext",
                    "-layout",
                    "-enc",
                    "UTF-8",
                    str(Path(temporary.name)),
                    "-",
                ],
                check=False,
                capture_output=True,
                timeout=COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("pdftotext timed out") from exc

    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(detail or "pdftotext could not process the PDF")

    return split_pages(result.stdout.decode("utf-8", errors="replace"))


@app.get("/health")
def health() -> dict[str, str | bool]:
    return {
        "status": "ok",
        "engine": "pdftotext",
        "executable_available": bool(shutil.which("pdftotext")),
    }


@app.post("/extract", response_model=ExtractionResponse)
async def extract(file: Annotated[UploadFile, File()]) -> ExtractionResponse:
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The uploaded file is too large.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=415, detail="Upload a valid PDF file.")

    started = time.perf_counter()
    try:
        raw_pages = await run_in_threadpool(run_pdftotext, content)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    pages = [
        PageResult(page=index, text=text) for index, text in enumerate(raw_pages, 1)
    ]
    full_text = "\n\n".join(page.text for page in pages if page.text).strip()
    return ExtractionResponse(
        filename=file.filename or "document.pdf",
        text=full_text,
        page_count=len(pages),
        character_count=len(full_text),
        has_text_layer=bool(full_text),
        duration_ms=round((time.perf_counter() - started) * 1000),
        pages=pages,
    )
