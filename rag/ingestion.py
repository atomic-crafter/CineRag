import vectorstore
from chunker import chunk_document
from embeddings import embed_texts
from loaders import load_document


def ingest_file(file_id: str, filename: str, file_path: str, s3_key: str | None = None) -> int:
    """Loads, chunks, embeds and stores a file, replacing any existing chunks. Returns chunk count."""
    pages = load_document(file_path)
    chunks = chunk_document(pages)

    vectorstore.delete_chunks(file_id)
    vectorstore.upsert_document(file_id, filename, s3_key, 0)

    if chunks:
        embeddings = embed_texts([c.chunk_text for c in chunks])
        vectorstore.insert_chunks(file_id, chunks, embeddings)

    vectorstore.upsert_document(file_id, filename, s3_key, len(chunks))
    return len(chunks)
