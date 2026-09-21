"""UI-facing /api routes used by the Angular frontend (documents CRUD + chat)."""

import mimetypes
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

import vectorstore
from embeddings import embed_texts
from generator import generate_answer
from ingestion import ingest_file

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/app/uploads"))
ALLOWED_EXTENSIONS = {".pdf", ".ppt", ".pptx"}
TOP_K = 5

router = APIRouter(prefix="/api")


def _document_json(file_id: str, filename: str, uploaded_at) -> dict:
    stored = next(UPLOAD_DIR.glob(f"{file_id}.*"), None)
    return {
        "id": file_id,
        "name": filename,
        "size": stored.stat().st_size if stored else 0,
        "type": mimetypes.guess_type(filename)[0] or "application/octet-stream",
        "uploadedAt": uploaded_at.isoformat(),
        "status": "ready",
    }


@router.get("/documents")
def list_documents():
    return [_document_json(*row) for row in vectorstore.list_documents()]


@router.post("/documents")
def upload_document(file: UploadFile = File(...)):
    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"unsupported file type: {ext or 'none'}")

    file_id = str(uuid.uuid4())
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored = UPLOAD_DIR / f"{file_id}{ext}"
    with stored.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        ingest_file(file_id, filename, str(stored))
    except Exception as e:
        stored.unlink(missing_ok=True)
        vectorstore.delete_document(file_id)
        raise HTTPException(status_code=422, detail=f"could not ingest {filename}: {e}")

    row = next(r for r in vectorstore.list_documents() if r[0] == file_id)
    return _document_json(*row)


@router.delete("/documents/{file_id}")
def delete_document(file_id: str):
    vectorstore.delete_document(file_id)
    for stored in UPLOAD_DIR.glob(f"{file_id}.*"):
        stored.unlink(missing_ok=True)
    return {"status": "deleted", "id": file_id}


class ChatRequest(BaseModel):
    question: str
    documentIds: list[str] = []


@router.post("/chat")
def chat(req: ChatRequest):
    if not req.documentIds:
        return {"answer": "Aucun document sélectionné : cochez au moins un document.", "sources": []}

    query_embedding = embed_texts([req.question])[0]
    results = vectorstore.search(query_embedding, top_k=TOP_K, file_ids=req.documentIds)
    answer = generate_answer(req.question, results)
    sources = list(dict.fromkeys(r.filename for r in results))
    return {"answer": answer, "sources": sources}
