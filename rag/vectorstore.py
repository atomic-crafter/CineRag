from dataclasses import dataclass

from pgvector import Vector

from chunker import Chunk
from db import pool


@dataclass
class SearchResult:
    file_id: str
    filename: str
    page_number: int | None
    chunk_text: str
    distance: float


def delete_chunks(file_id: str) -> int:
    with pool.connection() as conn:
        cur = conn.execute("DELETE FROM chunks WHERE file_id = %s", (file_id,))
        return cur.rowcount


def insert_chunks(file_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO chunks (file_id, chunk_index, page_number, chunk_text, embedding)
                VALUES (%s, %s, %s, %s, %s)
                """,
                [
                    (file_id, c.chunk_index, c.page_number, c.chunk_text, Vector(embedding))
                    for c, embedding in zip(chunks, embeddings)
                ],
            )
        # The ivfflat index is built (with degenerate centroids) on an empty
        # table at schema-init time, which silently drops rows from result
        # sets until reindexed against real data. Cheap at this scale.
        conn.execute("REINDEX INDEX idx_chunks_embedding")
        conn.commit()
    return len(chunks)


def upsert_document(file_id: str, filename: str, s3_key: str | None, chunk_count: int) -> None:
    with pool.connection() as conn:
        conn.execute(
            """
            INSERT INTO documents (file_id, filename, s3_key, status, chunk_count, updated_at)
            VALUES (%s, %s, %s, 'ready', %s, now())
            ON CONFLICT (file_id) DO UPDATE
            SET filename = EXCLUDED.filename,
                s3_key = EXCLUDED.s3_key,
                status = 'ready',
                chunk_count = EXCLUDED.chunk_count,
                updated_at = now()
            """,
            (file_id, filename, s3_key, chunk_count),
        )
        conn.commit()


def list_documents() -> list[tuple]:
    with pool.connection() as conn:
        cur = conn.execute(
            "SELECT file_id, filename, uploaded_at FROM documents ORDER BY uploaded_at"
        )
        return cur.fetchall()


def delete_document(file_id: str) -> int:
    with pool.connection() as conn:
        cur = conn.execute("SELECT chunk_count FROM documents WHERE file_id = %s", (file_id,))
        row = cur.fetchone()
        chunk_count = row[0] if row else 0
        conn.execute("DELETE FROM documents WHERE file_id = %s", (file_id,))
        conn.commit()
    return chunk_count


def search(
    query_embedding: list[float], top_k: int = 5, file_ids: list[str] | None = None
) -> list[SearchResult]:
    with pool.connection() as conn:
        if file_ids:
            cur = conn.execute(
                """
                SELECT c.file_id, d.filename, c.page_number, c.chunk_text,
                       c.embedding <=> %s AS distance
                FROM chunks c
                JOIN documents d ON d.file_id = c.file_id
                WHERE c.file_id = ANY(%s)
                ORDER BY distance
                LIMIT %s
                """,
                (Vector(query_embedding), file_ids, top_k),
            )
        else:
            cur = conn.execute(
                """
                SELECT c.file_id, d.filename, c.page_number, c.chunk_text,
                       c.embedding <=> %s AS distance
                FROM chunks c
                JOIN documents d ON d.file_id = c.file_id
                ORDER BY distance
                LIMIT %s
                """,
                (Vector(query_embedding), top_k),
            )
        rows = cur.fetchall()
    return [
        SearchResult(
            file_id=r[0], filename=r[1], page_number=r[2], chunk_text=r[3], distance=r[4]
        )
        for r in rows
    ]
