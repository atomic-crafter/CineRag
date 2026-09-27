import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.responses import JSONResponse

import db
import vectorstore
import webapi
from embeddings import embed_texts
from generator import generate_answer
from ingestion import ingest_file

API_KEY = os.environ["API_KEY"]
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:4200").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.open_pool()
    yield
    db.close_pool()


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    path = request.url.path
    # /health is for container probes; /api/* is the browser-facing UI layer (no key in the browser).
    if path != "/health" and not path.startswith("/api/"):
        if request.headers.get("X-API-Key") != API_KEY:
            return JSONResponse(status_code=401, content={"detail": "invalid or missing API key"})
    return await call_next(request)


# Added after the auth middleware so it is outermost and answers CORS preflights first.
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(webapi.router)


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
        chunks_added = ingest_file(req.file_id, req.filename, req.file_path, req.s3_key)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"file not found: {req.file_path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return IngestResponse(status="success", file_id=req.file_id, chunks_added=chunks_added)


class DeleteResponse(BaseModel):
    status: str
    file_id: str
    chunks_removed: int


@app.delete("/ingest/{file_id}", response_model=DeleteResponse)
def delete_ingest(file_id: str):
    chunks_removed = vectorstore.delete_document(file_id)
    return DeleteResponse(status="deleted", file_id=file_id, chunks_removed=chunks_removed)


class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    file_ids: list[str] | None = None


class Source(BaseModel):
    file_id: str
    filename: str
    page: int | None
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest):
    query_embedding = embed_texts([req.question])[0]
    results = vectorstore.search(query_embedding, top_k=req.top_k, file_ids=req.file_ids)

    answer = generate_answer(req.question, results)

    sources = [
        Source(file_id=r.file_id, filename=r.filename, page=r.page_number, snippet=r.chunk_text)
        for r in results
    ]
    return QueryResponse(answer=answer, sources=sources)
