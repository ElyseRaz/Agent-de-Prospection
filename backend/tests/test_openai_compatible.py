import json

import httpx
import pytest

from app.normalization.llm_common import ExtractionValidationError
from app.normalization.openai_compatible import call_openai_compatible_json
from app.normalization.risk_schema import RiskAssessment
from app.normalization.schema import ExtractedJobLLM

pytestmark = pytest.mark.asyncio


def _chat_completion_response(content: dict, *, prompt_tokens=100, completion_tokens=50) -> dict:
    return {
        "id": "chatcmpl-test",
        "choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}],
        "usage": {"prompt_tokens": prompt_tokens, "completion_tokens": completion_tokens},
    }


async def test_call_openai_compatible_json_parses_success():
    payload = _chat_completion_response({"risk_score": 20, "reasons": []})

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://opencode.ai/zen/go/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["model"] == "gpt-5.6-luna"
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    parsed, usage = await call_openai_compatible_json(
        client,
        base_url="https://opencode.ai/zen/go/v1",
        api_key="test-key",
        model="gpt-5.6-luna",
        system_prompt="system",
        user_text="user",
        output_type=RiskAssessment,
    )

    assert isinstance(parsed, RiskAssessment)
    assert parsed.risk_score == 20
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    await client.aclose()


async def test_call_openai_compatible_json_strips_trailing_slash_from_base_url():
    payload = _chat_completion_response({"risk_score": 0, "reasons": []})
    called_urls = []

    def handler(request: httpx.Request) -> httpx.Response:
        called_urls.append(str(request.url))
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await call_openai_compatible_json(
        client,
        base_url="https://opencode.ai/zen/go/v1/",
        api_key="k",
        model="gpt-5.6-luna",
        system_prompt="s",
        user_text="u",
        output_type=RiskAssessment,
    )

    assert called_urls == ["https://opencode.ai/zen/go/v1/chat/completions"]
    await client.aclose()


async def test_call_openai_compatible_json_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad key")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(ExtractionValidationError):
        await call_openai_compatible_json(
            client,
            base_url="https://opencode.ai/zen/go/v1",
            api_key="wrong",
            model="gpt-5.6-luna",
            system_prompt="s",
            user_text="u",
            output_type=RiskAssessment,
        )
    await client.aclose()


async def test_call_openai_compatible_json_raises_on_invalid_json_content():
    payload = {
        "choices": [{"message": {"role": "assistant", "content": "not json at all"}}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(ExtractionValidationError):
        await call_openai_compatible_json(
            client,
            base_url="https://opencode.ai/zen/go/v1",
            api_key="k",
            model="gpt-5.6-luna",
            system_prompt="s",
            user_text="u",
            output_type=RiskAssessment,
        )
    await client.aclose()


async def test_call_openai_compatible_json_raises_on_schema_mismatch():
    payload = _chat_completion_response({"unexpected": "shape"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    with pytest.raises(ExtractionValidationError):
        await call_openai_compatible_json(
            client,
            base_url="https://opencode.ai/zen/go/v1",
            api_key="k",
            model="gpt-5.6-luna",
            system_prompt="s",
            user_text="u",
            output_type=RiskAssessment,
        )
    await client.aclose()


async def test_call_openai_compatible_json_missing_usage_defaults_to_zero():
    payload = {"choices": [{"message": {"content": '{"risk_score": 5, "reasons": []}'}}]}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    _parsed, usage = await call_openai_compatible_json(
        client,
        base_url="https://opencode.ai/zen/go/v1",
        api_key="k",
        model="gpt-5.6-luna",
        system_prompt="s",
        user_text="u",
        output_type=RiskAssessment,
    )

    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.cost_usd == 0.0  # aucun tarif public connu pour ce modele
    await client.aclose()


async def test_call_openai_compatible_json_works_with_job_extraction_schema():
    payload = _chat_completion_response({"title": "Dev Python", "tech_stack": ["python"]})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    parsed, _usage = await call_openai_compatible_json(
        client,
        base_url="https://opencode.ai/zen/go/v1",
        api_key="k",
        model="gpt-5.6-luna",
        system_prompt="s",
        user_text="u",
        output_type=ExtractedJobLLM,
    )

    assert isinstance(parsed, ExtractedJobLLM)
    assert parsed.title == "Dev Python"
    await client.aclose()
