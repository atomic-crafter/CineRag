from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

# ~4 chars/token heuristic: 500-800 tokens ~= 2000-3200 chars.
CHUNK_SIZE = 2800
CHUNK_OVERLAP = 300

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)


@dataclass
class Chunk:
    chunk_index: int
    page_number: int | None
    chunk_text: str


def chunk_document(pages: list[tuple[int, str]]) -> list[Chunk]:
    """Chunks (page_number, text) pairs into overlapping text chunks, preserving page_number."""
    chunks: list[Chunk] = []
    index = 0
    for page_number, text in pages:
        for piece in _splitter.split_text(text):
            if not piece.strip():
                continue
            chunks.append(Chunk(chunk_index=index, page_number=page_number, chunk_text=piece))
            index += 1
    return chunks
