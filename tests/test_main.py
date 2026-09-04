from unittest.mock import patch

from fastapi.testclient import TestClient

from main import app, split_pages

client = TestClient(app)


def test_split_pages_removes_trailing_form_feed() -> None:
    assert split_pages("Page one\fPage two\f") == ["Page one", "Page two"]


@patch("main.run_pdftotext")
def test_extract(mock_run_pdftotext) -> None:
    mock_run_pdftotext.return_value = ["Page one", "Page two"]

    response = client.post(
        "/extract",
        files={"file": ("sample.pdf", b"%PDF-1.7\nmock", "application/pdf")},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["engine"] == "pdftotext"
    assert result["page_count"] == 2
    assert result["has_text_layer"] is True
    assert result["text"] == "Page one\n\nPage two"


def test_rejects_non_pdf() -> None:
    response = client.post(
        "/extract",
        files={"file": ("sample.txt", b"plain text", "text/plain")},
    )
    assert response.status_code == 415
