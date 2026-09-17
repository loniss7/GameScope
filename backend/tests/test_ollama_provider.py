import asyncio
import json

import httpx
import pytest

from app.ai.base import AiProviderError
from app.ai.ollama import OllamaProvider
from app.schemas import GameReview


def _reviews() -> list[GameReview]:
    return [
        GameReview(
            source="steam",
            text="Great story and atmosphere.",
            voted_up=True,
        ),
        GameReview(
            source="steam",
            text="The performance is poor on older hardware.",
            voted_up=False,
        ),
    ]


def test_ollama_provider_returns_validated_summary() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "message": {
                    "role": "assistant",
                    "content": (
                        '{"summary":"Mostly positive.",'
                        '"pros":["story"],"cons":["performance"],'
                        '"sentiment":{"positive":0.8,"negative":0.2,"neutral":0}}'
                    ),
                }
            },
        )

    async def exercise():
        provider = OllamaProvider(
            base_url="http://ollama.test",
            model="qwen3:8b",
            transport=httpx.MockTransport(handler),
        )
        try:
            return await provider.summarize_reviews(
                "Example Game", _reviews(), language="ru"
            )
        finally:
            await provider.aclose()

    summary = asyncio.run(exercise())
    assert summary.summary == "Mostly positive."
    assert summary.pros == ["story"]
    assert summary.cons == ["performance"]
    assert summary.reviews_analyzed == 2
    assert summary.model == "qwen3:8b"
    assert summary.source == "steam"
    assert len(requests) == 1
    body = json.loads(requests[0].content)
    assert body["model"] == "qwen3:8b"
    assert body["stream"] is False
    assert body["format"] == "json"
    assert body["think"] is False
    assert body["options"] == {
        "num_ctx": 4096,
        "num_predict": 512,
        "temperature": 0.2,
    }


def test_ollama_provider_accepts_json_code_fence() -> None:
    payload = {
        "message": {
            "content": (
                "```json\n"
                '{"summary":"Good.","pros":[],"cons":[],'
                '"sentiment":{"positive":1,"negative":0,"neutral":0}}\n'
                "```"
            )
        }
    }

    async def exercise():
        provider = OllamaProvider(
            transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
        )
        try:
            return await provider.summarize_reviews("Example", _reviews())
        finally:
            await provider.aclose()

    assert asyncio.run(exercise()).summary == "Good."


def test_ollama_provider_sanitizes_unavailable_service() -> None:
    async def exercise() -> None:
        provider = OllamaProvider(
            transport=httpx.MockTransport(
                lambda _: (_ for _ in ()).throw(httpx.ConnectError("offline"))
            )
        )
        try:
            with pytest.raises(AiProviderError, match="connect"):
                await provider.summarize_reviews("Example", _reviews())
        finally:
            await provider.aclose()

    asyncio.run(exercise())
