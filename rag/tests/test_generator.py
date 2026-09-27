import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import generator
import vectorstore

RESULTS = [
    vectorstore.SearchResult(
        file_id="f1", filename="doc.pdf", page_number=1, chunk_text="the sky is blue", distance=0.1
    )
]


def test_bedrock_provider_calls_converse_with_prompt(monkeypatch):
    calls = {}

    class FakeClient:
        def converse(self, **kwargs):
            calls["kwargs"] = kwargs
            return {"output": {"message": {"content": [{"text": "bedrock answer"}]}}}

    fake_boto3 = types.SimpleNamespace(
        client=lambda service, region_name: calls.update(service=service, region=region_name)
        or FakeClient()
    )
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.setattr(generator, "LLM_PROVIDER", "bedrock")
    monkeypatch.setattr(generator, "BEDROCK_MODEL_ID", "test-model")
    monkeypatch.setattr(generator, "BEDROCK_REGION", "eu-west-3")

    answer = generator.generate_answer("what colour is the sky?", RESULTS)

    assert answer == "bedrock answer"
    assert calls["service"] == "bedrock-runtime"
    assert calls["region"] == "eu-west-3"
    assert calls["kwargs"]["modelId"] == "test-model"
    sent = calls["kwargs"]["messages"][0]["content"][0]["text"]
    assert "the sky is blue" in sent and "what colour is the sky?" in sent


def test_openai_provider_is_the_default(monkeypatch):
    monkeypatch.setattr(generator, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(generator, "_generate_openai", lambda prompt: "openai answer")
    monkeypatch.setattr(generator, "_generate_bedrock", lambda prompt: 1 / 0)
    assert generator.generate_answer("q", RESULTS) == "openai answer"
