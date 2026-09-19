import os

import httpx

from vectorstore import SearchResult

ZAI_API_KEY = os.environ["ZAI_API_KEY"]
ZAI_BASE_URL = os.environ["ZAI_BASE_URL"]
ZAI_MODEL = os.environ.get("ZAI_MODEL", "glm-4")

PROMPT_TEMPLATE = """You are a helpful assistant answering questions using only the provided context. \
If the context does not contain the answer, say you don't know.

Context:
{context}

Question: {question}

Answer:"""


def build_prompt(question: str, results: list[SearchResult]) -> str:
    context = "\n\n".join(
        f"[{i + 1}] (source: {r.filename}, page {r.page_number}) {r.chunk_text}"
        for i, r in enumerate(results)
    )
    return PROMPT_TEMPLATE.format(context=context, question=question)


def generate_answer(question: str, results: list[SearchResult]) -> str:
    prompt = build_prompt(question, results)
    response = httpx.post(
        f"{ZAI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {ZAI_API_KEY}"},
        json={
            "model": ZAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]
