import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

import app as app_module
import generator
import vectorstore
from chunker import Chunk
from embeddings import embed_texts


@pytest.fixture
def seeded_docs(client):
    """Inserts two documents with distinct content, cleans up afterwards."""
    docs = {
        "q-doc-cats": [
            Chunk(chunk_index=0, page_number=1, chunk_text="The cat sat on the warm mat."),
        ],
        "q-doc-rockets": [
            Chunk(
                chunk_index=0,
                page_number=1,
                chunk_text="Rockets launch into orbit using powerful engines.",
            ),
        ],
    }
    for file_id, chunks in docs.items():
        vectorstore.delete_chunks(file_id)
        vectorstore.upsert_document(file_id, f"{file_id}.pdf", None, 0)
        embeddings = embed_texts([c.chunk_text for c in chunks])
        vectorstore.insert_chunks(file_id, chunks, embeddings)
        vectorstore.upsert_document(file_id, f"{file_id}.pdf", None, len(chunks))

    yield docs

    for file_id in docs:
        vectorstore.delete_document(file_id)





def test_query_returns_answer_and_sources(client, seeded_docs, monkeypatch):
    captured = {}

    def fake_generate_answer(question, results):
        captured["question"] = question
        captured["results"] = results
        return "a rocket is a vehicle that launches into orbit"

    monkeypatch.setattr(app_module, "generate_answer", fake_generate_answer)

    resp = client.post(
        "/query",
        json={"question": "How do rockets get to orbit?", "top_k": 2},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "a rocket is a vehicle that launches into orbit"
    assert len(body["sources"]) == 2
    assert body["sources"][0]["file_id"] == "q-doc-rockets"
    assert "snippet" in body["sources"][0]
    assert captured["question"] == "How do rockets get to orbit?"


def test_query_filters_by_file_ids(client, seeded_docs, monkeypatch):
    monkeypatch.setattr(app_module, "generate_answer", lambda q, r: "stub answer")

    resp = client.post(
        "/query",
        json={
            "question": "How do rockets get to orbit?",
            "top_k": 5,
            "file_ids": ["q-doc-cats"],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["sources"]) == 1
    assert body["sources"][0]["file_id"] == "q-doc-cats"


def test_build_prompt_includes_context_and_question():
    results = [
        vectorstore.SearchResult(
            file_id="f1", filename="doc.pdf", page_number=3, chunk_text="some fact", distance=0.1
        )
    ]
    prompt = generator.build_prompt("What is the fact?", results)
    assert "some fact" in prompt
    assert "doc.pdf" in prompt
    assert "page 3" in prompt
    assert "What is the fact?" in prompt
