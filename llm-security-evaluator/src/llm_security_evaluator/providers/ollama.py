"""Ollama HTTP API integration with bounded retries."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from ..errors import ModelNotFoundError, ProviderError
from ..models import GenerationConfig, ProviderConfig


@dataclass(slots=True)
class ProviderResponse:
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OllamaProvider:
    def __init__(
        self, config: ProviderConfig, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.config = config
        self._client = httpx.Client(
            base_url=config.endpoint.rstrip("/"), timeout=config.timeout, transport=transport
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> OllamaProvider:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def list_models(self) -> list[str]:
        try:
            response = self._client.get("/api/tags")
            response.raise_for_status()
            payload = response.json()
            return sorted(item["name"] for item in payload.get("models", []) if item.get("name"))
        except (httpx.HTTPError, ValueError, TypeError, KeyError) as exc:
            raise ProviderError(self._safe_http_message(exc)) from exc

    def generate(
        self, prompt: str, system_prompt: str, generation: GenerationConfig
    ) -> ProviderResponse:
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": generation.temperature,
                "num_predict": generation.max_tokens,
                **({"seed": generation.seed} if generation.seed is not None else {}),
            },
        }
        for attempt in range(self.config.retries + 1):
            try:
                response = self._client.post("/api/generate", json=payload)
                if response.status_code == 404:
                    raise ModelNotFoundError(
                        f"Ollama model '{self.config.model}' is not installed. "
                        f"Run: ollama pull {self.config.model}"
                    )
                response.raise_for_status()
                data = response.json()
                text = data.get("response")
                if not isinstance(text, str) or not text.strip():
                    raise ProviderError("Ollama returned an empty model response.")
                return ProviderResponse(
                    text=text,
                    prompt_tokens=_optional_int(data.get("prompt_eval_count")),
                    completion_tokens=_optional_int(data.get("eval_count")),
                    metadata={
                        "done_reason": data.get("done_reason"),
                        "total_duration_ns": data.get("total_duration"),
                    },
                )
            except ModelNotFoundError:
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                if attempt < self.config.retries:
                    time.sleep(min(0.25 * (2**attempt), 1.0))
                    continue
                raise ProviderError(self._safe_http_message(exc)) from exc
            except (httpx.HTTPError, ValueError, TypeError) as exc:
                raise ProviderError(self._safe_http_message(exc)) from exc
        raise ProviderError("Ollama request failed.")  # pragma: no cover

    @staticmethod
    def _safe_http_message(exc: Exception) -> str:
        if isinstance(exc, httpx.TimeoutException):
            return "Ollama request timed out. Check the configured timeout and local server."
        if isinstance(exc, httpx.ConnectError):
            return "Could not connect to Ollama. Start it locally with 'ollama serve'."
        if isinstance(exc, httpx.HTTPStatusError):
            return f"Ollama returned HTTP {exc.response.status_code}."
        return "Ollama returned an invalid response."


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None
