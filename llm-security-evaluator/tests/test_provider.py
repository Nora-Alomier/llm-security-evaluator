import httpx
import pytest

from llm_security_evaluator.errors import ModelNotFoundError, ProviderError
from llm_security_evaluator.models import GenerationConfig, ProviderConfig
from llm_security_evaluator.providers import OllamaProvider


def provider(handler) -> OllamaProvider:
    return OllamaProvider(ProviderConfig(retries=0), httpx.MockTransport(handler))


def test_parses_ollama_response() -> None:
    def handler(request):
        return httpx.Response(
            200,
            json={
                "response": "Safe",
                "prompt_eval_count": 8,
                "eval_count": 2,
                "done_reason": "stop",
            },
        )

    with provider(handler) as client:
        response = client.generate("prompt", "system", GenerationConfig())
    assert response.text == "Safe"
    assert response.prompt_tokens == 8
    assert response.completion_tokens == 2


def test_model_not_found() -> None:
    with (
        provider(lambda request: httpx.Response(404, json={"error": "not found"})) as client,
        pytest.raises(ModelNotFoundError, match="ollama pull"),
    ):
        client.generate("p", "s", GenerationConfig())


def test_empty_response() -> None:
    with (
        provider(lambda request: httpx.Response(200, json={"response": ""})) as client,
        pytest.raises(ProviderError, match="empty"),
    ):
        client.generate("p", "s", GenerationConfig())


def test_timeout_is_safe_error() -> None:
    def timeout(request):
        raise httpx.ReadTimeout("details", request=request)

    with provider(timeout) as client, pytest.raises(ProviderError, match="timed out"):
        client.generate("p", "s", GenerationConfig())


def test_lists_models() -> None:
    with provider(
        lambda request: httpx.Response(200, json={"models": [{"name": "llama3.2:latest"}]})
    ) as client:
        assert client.list_models() == ["llama3.2:latest"]
