# RAG microservice

Standalone retrieval-augmented generation backend. FastAPI + Postgres/pgvector
for storage and vector search, `sentence-transformers` for embeddings, Z.AI
GLM for answer generation.

## Running locally

```bash
cp .env.example .env
# edit .env and set ZAI_API_KEY

docker compose up -d --build
curl http://localhost:8000/health
```

All endpoints except `/health` require an `X-API-Key` header matching the
`API_KEY` value in `.env`.

## Endpoints

### `GET /health`

No auth required.

```bash
curl http://localhost:8000/health
```

```json
{"status": "ok"}
```

### `POST /ingest`

Loads a PDF or PPTX from a local path, chunks it, embeds each chunk, and
(re)inserts it into the vector store. Re-ingesting the same `file_id`
replaces its existing chunks.

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
        "file_id": "doc-1",
        "filename": "syllabus.pdf",
        "file_path": "/data/syllabus.pdf"
      }'
```

```json
{"status": "success", "file_id": "doc-1", "chunks_added": 12}
```

### `DELETE /ingest/{file_id}`

Deletes the document row (cascades to its chunks).

```bash
curl -X DELETE http://localhost:8000/ingest/doc-1 \
  -H "X-API-Key: changeme"
```

```json
{"status": "deleted", "file_id": "doc-1", "chunks_removed": 12}
```

### `POST /query`

Embeds the question, does a vector search (optionally restricted to
`file_ids`), and asks the LLM to answer using the retrieved chunks.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: changeme" \
  -d '{
        "question": "When is the midterm?",
        "top_k": 5,
        "file_ids": ["doc-1"]
      }'
```

`file_ids` is optional — omit it (or pass `null`) to search across all
ingested documents.

```json
{
  "answer": "The midterm is on October 14th.",
  "sources": [
    {
      "file_id": "doc-1",
      "filename": "syllabus.pdf",
      "page": 3,
      "snippet": "The midterm exam will be held on October 14th..."
    }
  ]
}
```

## Web UI routes (`/api`)

Used by the Angular frontend in `Front/FrontCineRag`. These routes are called from
the browser, so they do **not** require `X-API-Key` (the browser can't hold a
secret); CORS allows `http://localhost:4200` (override with `CORS_ORIGINS`).
Uploaded files are stored in `UPLOAD_DIR` (default `/app/uploads`).

| Route                       | Purpose                                                       |
|-----------------------------|---------------------------------------------------------------|
| `GET /api/documents`        | List documents                                                |
| `POST /api/documents`       | Multipart upload (`file` field; `.pdf`, `.ppt`, `.pptx`), ingests it |
| `DELETE /api/documents/{id}`| Delete a document and its stored file                         |
| `POST /api/chat`            | `{"question": str, "documentIds": [str]}` -> `{"answer", "sources": [filenames]}` |

Run the UI with `cd Front/FrontCineRag && npm ci && npx ng serve` (http://localhost:4200)
while `docker compose up -d` is running.

## Environment variables

See `.env.example`:

| Variable        | Purpose                                              |
|-----------------|-------------------------------------------------------|
| `DATABASE_URL`  | Postgres connection string                            |
| `ZAI_API_KEY`   | Z.AI GLM API key (do not commit)                       |
| `ZAI_BASE_URL`  | Z.AI OpenAI-compatible base URL                        |
| `API_KEY`       | Shared secret required in the `X-API-Key` header       |

## Tests

Unit tests for loaders/chunking run standalone. Integration tests for the
`/ingest` and `/query` endpoints require the `db` service to be running
(`docker compose up -d db`) and hit it directly on `localhost:5432`.

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://rag:ragpass@localhost:5432/ragdb \
API_KEY=test-key ZAI_API_KEY=unused ZAI_BASE_URL=http://unused.invalid \
pytest tests/ -v
```
