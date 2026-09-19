from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import db
import vectorstore
from chunker import chunk_document
from embeddings import embed_texts
from loaders import load_document


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


class IngestRequest(BaseModel):
    file_id: str
    filename: str
    file_path: str
    s3_key: str | None = None


class IngestResponse(BaseModel):
    status: str
    file_id: str
    chunks_added: int


@app.post("/ingest", response_model=IngestResponse)
def ingest(req: IngestRequest):
    try:
        pages = load_document(req.file_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"file not found: {req.file_path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chunks = chunk_document(pages)

    vectorstore.delete_chunks(req.file_id)
    vectorstore.upsert_document(req.file_id, req.filename, req.s3_key, 0)

    if chunks:
        embeddings = embed_texts([c.chunk_text for c in chunks])
        vectorstore.insert_chunks(req.file_id, chunks, embeddings)

    vectorstore.upsert_document(req.file_id, req.filename, req.s3_key, len(chunks))

    return IngestResponse(status="success", file_id=req.file_id, chunks_added=len(chunks))


class DeleteResponse(BaseModel):
    status: str
    file_id: str
    chunks_removed: int


@app.delete("/ingest/{file_id}", response_model=DeleteResponse)
def delete_ingest(file_id: str):
    chunks_removed = vectorstore.delete_document(file_id)
    return DeleteResponse(status="deleted", file_id=file_id, chunks_removed=chunks_removed)
