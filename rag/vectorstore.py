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


# Arbitrary constant, just needs to be the same value everywhere it's used.
_REINDEX_LOCK_KEY = 727276


def insert_chunks(file_id: str, chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    with pool.connection() as conn:
        with conn.cursor() as cur:
            was_empty = conn.execute("SELECT NOT EXISTS (SELECT 1 FROM chunks)").fetchone()[0]
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
        conn.commit()

    # The ivfflat index is built (with degenerate centroids) on an empty
    # table at schema-init time, which silently drops rows from result sets
    # until reindexed against real data - so this only needs to run for the
    # very first insert (was_empty), not on every upload: once the index has
    # real data, ordinary ivfflat recall degrades gracefully instead of
    # dropping rows outright. REINDEX CONCURRENTLY avoids the exclusive lock
    # a plain REINDEX takes, which would otherwise stall every other query
    # (chats included) while one upload reindexes - it must run outside a
    # transaction, hence its own autocommit connection.
    #
    # pg_try_advisory_lock (never blocks), not pg_advisory_lock: if several
    # first-uploads race, only the winner needs to reindex - it fixes the
    # one shared index for everyone. A *blocking* lock here would deadlock:
    # a backend parked waiting on pg_advisory_lock still holds an open
    # snapshot, which is exactly what REINDEX CONCURRENTLY's "wait for old
    # snapshots" phase then waits on - so the reindexer waits for the
    # waiter, and the waiter waits for the reindexer. Confirmed by testing
    # concurrent first-uploads before switching to try-lock.
    if was_empty:
        with pool.connection() as conn:
            conn.autocommit = True
            got_lock = conn.execute(
                "SELECT pg_try_advisory_lock(%s)", (_REINDEX_LOCK_KEY,)
            ).fetchone()[0]
            if got_lock:
                try:
                    conn.execute("REINDEX INDEX CONCURRENTLY idx_chunks_embedding")
                finally:
                    conn.execute("SELECT pg_advisory_unlock(%s)", (_REINDEX_LOCK_KEY,))
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
