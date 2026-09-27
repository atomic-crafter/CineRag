from sentence_transformers import SentenceTransformer

EMBEDDING_DIM = 384
_MODEL_NAME = "all-MiniLM-L6-v2"

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = _get_model().encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]
