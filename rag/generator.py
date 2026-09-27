import os

import httpx

from vectorstore import SearchResult

# "openai" = any OpenAI-compatible chat endpoint (Z.AI, Ollama); "bedrock" = Amazon Bedrock.
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "openai")

ZAI_API_KEY = os.environ.get("ZAI_API_KEY", "")
ZAI_BASE_URL = os.environ.get("ZAI_BASE_URL", "")
ZAI_MODEL = os.environ.get("ZAI_MODEL", "glm-4")

BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "eu.amazon.nova-lite-v1:0")
BEDROCK_REGION = os.environ.get("BEDROCK_REGION") or os.environ.get("AWS_REGION", "eu-west-3")

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


def _generate_bedrock(prompt: str) -> str:
    import boto3  # imported lazily so the openai provider needs no AWS setup

    client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    response = client.converse(
        modelId=BEDROCK_MODEL_ID,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
        inferenceConfig={"maxTokens": 1024, "temperature": 0.2},
    )
    return response["output"]["message"]["content"][0]["text"]


def _generate_openai(prompt: str) -> str:
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


def generate_answer(question: str, results: list[SearchResult]) -> str:
    prompt = build_prompt(question, results)
    if LLM_PROVIDER == "bedrock":
        return _generate_bedrock(prompt)
    return _generate_openai(prompt)
