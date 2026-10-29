"""Safe YAML/JSON configuration loading and validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from .assertions import ASSERTION_TYPES
from .errors import ConfigurationError
from .models import (
    AssertionConfig,
    EvaluationConfig,
    GenerationConfig,
    OutputConfig,
    ProviderConfig,
    TestCase,
)

SUPPORTED_FORMATS = {"json", "csv", "html"}


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{label} must be an object/mapping.")
    return value


def validate_local_endpoint(endpoint_value: str) -> None:
    """Reject non-loopback or credential-bearing inference endpoints."""
    endpoint = urlparse(endpoint_value)
    if (
        endpoint.scheme != "http"
        or endpoint.hostname not in {"localhost", "127.0.0.1", "::1"}
        or endpoint.username is not None
        or endpoint.password is not None
    ):
        raise ConfigurationError("Ollama endpoint must be a localhost URL.")


def load_config(path: str | Path) -> EvaluationConfig:
    config_path = Path(path).expanduser()
    if not config_path.is_file():
        raise ConfigurationError(f"Configuration file not found: {config_path}")
    if config_path.suffix.lower() not in {".yaml", ".yml", ".json"}:
        raise ConfigurationError("Configuration must use .yaml, .yml, or .json.")
    try:
        text = config_path.read_text(encoding="utf-8")
        raw = json.loads(text) if config_path.suffix.lower() == ".json" else yaml.safe_load(text)
    except (OSError, json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ConfigurationError(f"Could not parse configuration: {exc}") from exc
    return parse_config(_mapping(raw, "Configuration"))


def parse_config(raw: dict[str, Any]) -> EvaluationConfig:
    provider_data = _mapping(raw.get("provider", {}), "provider")
    if provider_data.get("name", "ollama") != "ollama":
        raise ConfigurationError("Only the local 'ollama' provider is currently supported.")
    provider = ProviderConfig(**_known(provider_data, ProviderConfig, "provider"))
    validate_local_endpoint(provider.endpoint)
    if not provider.model.strip() or provider.timeout <= 0 or provider.retries < 0:
        raise ConfigurationError("provider model, timeout, or retries is invalid.")

    generation_data = _mapping(raw.get("generation", {}), "generation")
    generation = GenerationConfig(**_known(generation_data, GenerationConfig, "generation"))
    if not 0 <= generation.temperature <= 2 or generation.max_tokens < 1:
        raise ConfigurationError(
            "generation.temperature must be 0..2 and max_tokens must be positive."
        )

    output_data = _mapping(raw.get("output", {}), "output")
    output = OutputConfig(**_known(output_data, OutputConfig, "output"))
    output_path = Path(output.directory)
    if not output.directory.strip() or output_path.is_absolute() or ".." in output_path.parts:
        raise ConfigurationError("output.directory must be a safe relative path.")
    output.formats = [str(value).lower() for value in output.formats]
    unknown_formats = set(output.formats) - SUPPORTED_FORMATS
    if not output.formats or unknown_formats:
        raise ConfigurationError(f"Invalid output formats: {sorted(unknown_formats)}")

    repetitions = raw.get("repetitions", 1)
    if not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 1:
        raise ConfigurationError("repetitions must be a positive integer.")
    system_prompt = raw.get("system_prompt")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise ConfigurationError("system_prompt is required and must not be empty.")
    tests_data = raw.get("tests")
    if not isinstance(tests_data, list) or not tests_data:
        raise ConfigurationError("tests must be a non-empty list.")

    tests = [_parse_test(value, index) for index, value in enumerate(tests_data)]
    ids = [test.id for test in tests]
    if len(ids) != len(set(ids)):
        raise ConfigurationError("Each test id must be unique.")
    return EvaluationConfig(
        name=str(raw.get("name", "LLM Security Evaluation")),
        provider=provider,
        generation=generation,
        output=output,
        system_prompt=system_prompt,
        tests=tests,
        repetitions=repetitions,
    )


def _known(data: dict[str, Any], model: type, label: str) -> dict[str, Any]:
    allowed = set(model.__dataclass_fields__)
    unknown = set(data) - allowed
    if unknown:
        raise ConfigurationError(f"Unknown {label} fields: {sorted(unknown)}")
    return data


def _parse_test(value: Any, index: int) -> TestCase:
    data = _mapping(value, f"tests[{index}]")
    for key in ("id", "category", "prompt", "assertions"):
        if key not in data:
            raise ConfigurationError(f"tests[{index}] is missing required field '{key}'.")
    if not all(
        isinstance(data[key], str) and data[key].strip() for key in ("id", "category", "prompt")
    ):
        raise ConfigurationError(
            f"tests[{index}] id, category, and prompt must be non-empty strings."
        )
    if not isinstance(data["assertions"], list) or not data["assertions"]:
        raise ConfigurationError(f"tests[{index}].assertions must be a non-empty list.")
    assertions = []
    for position, assertion in enumerate(data["assertions"]):
        item = _mapping(assertion, f"tests[{index}].assertions[{position}]")
        unknown = set(item) - {"type", "value", "case_sensitive"}
        if unknown or item.get("type") not in ASSERTION_TYPES:
            raise ConfigurationError(
                f"Invalid assertion at tests[{index}].assertions[{position}]: "
                f"type={item.get('type')!r}, unknown fields={sorted(unknown)}"
            )
        if item["type"] not in {"refusal"} and not isinstance(item.get("value"), str):
            raise ConfigurationError(f"Assertion '{item['type']}' requires a string value.")
        assertions.append(AssertionConfig(**item))
    repetitions = data.get("repetitions")
    if repetitions is not None and (
        not isinstance(repetitions, int) or isinstance(repetitions, bool) or repetitions < 1
    ):
        raise ConfigurationError(f"tests[{index}].repetitions must be a positive integer.")
    allowed = {
        "id",
        "category",
        "prompt",
        "assertions",
        "description",
        "system_prompt",
        "repetitions",
    }
    unknown = set(data) - allowed
    if unknown:
        raise ConfigurationError(f"Unknown tests[{index}] fields: {sorted(unknown)}")
    return TestCase(**{**data, "assertions": assertions})
