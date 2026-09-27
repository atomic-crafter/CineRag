import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vectorstore
import webapi
from test_ingest import _make_sample_pdf

ORIGIN = "http://localhost:4200"


def test_api_routes_need_no_api_key(client):
    assert client.get("/api/documents").status_code == 200


def test_non_api_routes_still_need_api_key(client):
    assert client.delete("/ingest/x").status_code == 401
    assert client.post("/query", json={"question": "hi"}).status_code == 401


def test_cors_preflight_allows_frontend_origin(client):
    resp = client.options(
        "/api/documents",
        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "POST"},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == ORIGIN


def test_upload_list_delete_roundtrip(client, tmp_path):
    pdf = _make_sample_pdf(tmp_path)
    with pdf.open("rb") as f:
        resp = client.post("/api/documents", files={"file": ("sample.pdf", f, "application/pdf")})
    assert resp.status_code == 200
    doc = resp.json()
    file_id = doc["id"]
    try:
        assert doc["name"] == "sample.pdf"
        assert doc["type"] == "application/pdf"
        assert doc["status"] == "ready"
        assert doc["size"] > 0

        listed = client.get("/api/documents").json()
        assert file_id in [d["id"] for d in listed]
    finally:
        resp = client.delete(f"/api/documents/{file_id}")
    assert resp.status_code == 200
    assert file_id not in [d["id"] for d in client.get("/api/documents").json()]
    assert not list(webapi.UPLOAD_DIR.glob(f"{file_id}.*"))


def test_upload_rejects_unsupported_type(client):
    resp = client.post("/api/documents", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_upload_unreadable_file_leaves_no_trace(client):
    before = {d["id"] for d in client.get("/api/documents").json()}
    resp = client.post("/api/documents", files={"file": ("bad.pdf", b"not a pdf", "application/pdf")})
    assert resp.status_code == 422
    assert {d["id"] for d in client.get("/api/documents").json()} == before


def test_chat_uses_selected_documents_and_returns_filenames(client, tmp_path, monkeypatch):
    pdf = _make_sample_pdf(tmp_path)
    with pdf.open("rb") as f:
        file_id = client.post(
            "/api/documents", files={"file": ("sample.pdf", f, "application/pdf")}
        ).json()["id"]
    monkeypatch.setattr(webapi, "generate_answer", lambda q, results: f"stub for {q}")
    try:
        resp = client.post("/api/chat", json={"question": "hello?", "documentIds": [file_id]})
        assert resp.status_code == 200
        assert resp.json() == {"answer": "stub for hello?", "sources": ["sample.pdf"]}
    finally:
        vectorstore.delete_document(file_id)


def test_chat_without_selection_skips_the_llm(client, monkeypatch):
    def boom(*args):
        raise AssertionError("LLM must not be called without a selection")

    monkeypatch.setattr(webapi, "generate_answer", boom)
    resp = client.post("/api/chat", json={"question": "hello?", "documentIds": []})
    assert resp.status_code == 200
    assert resp.json()["sources"] == []
