"""Typed domain models used by the engine and reporters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"


@dataclass(slots=True)
class AssertionConfig:
    type: str
    value: str | None = None
    case_sensitive: bool = True


@dataclass(slots=True)
class TestCase:
    id: str
    category: str
    prompt: str
    assertions: list[AssertionConfig]
    description: str = ""
    system_prompt: str | None = None
    repetitions: int | None = None


@dataclass(slots=True)
class ProviderConfig:
    name: str = "ollama"
    endpoint: str = "http://localhost:11434"
    model: str = "llama3.2"
    timeout: float = 60.0
    retries: int = 2


@dataclass(slots=True)
class GenerationConfig:
    temperature: float = 0.0
    max_tokens: int = 512
    seed: int | None = 42


@dataclass(slots=True)
class OutputConfig:
    directory: str = "results"
    formats: list[str] = field(default_factory=lambda: ["json", "csv", "html"])


@dataclass(slots=True)
class EvaluationConfig:
    provider: ProviderConfig
    generation: GenerationConfig
    output: OutputConfig
    system_prompt: str
    tests: list[TestCase]
    repetitions: int = 1
    name: str = "LLM Security Evaluation"


@dataclass(slots=True)
class AssertionResult:
    type: str
    passed: bool
    reason: str


@dataclass(slots=True)
class EvaluationResult:
    test_id: str
    category: str
    prompt: str
    response: str
    status: Status
    duration_ms: float
    repetition: int
    assertions: list[AssertionResult] = field(default_factory=list)
    error: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Summary:
    total: int
    passed: int
    failed: int
    errors: int
    pass_rate: float
    failure_rate: float


@dataclass(slots=True)
class EvaluationRun:
    name: str
    model: str
    provider: str
    endpoint: str
    started_at: str
    completed_at: str
    generation: dict[str, Any]
    summary: Summary
    results: list[EvaluationResult]
    tool_version: str = "0.1.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def now_iso(cls) -> str:
        return datetime.now(UTC).isoformat()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationRun:
        results = []
        for item in data["results"]:
            assertions = [AssertionResult(**value) for value in item.get("assertions", [])]
            results.append(
                EvaluationResult(
                    **{k: v for k, v in item.items() if k not in {"assertions", "status"}},
                    assertions=assertions,
                    status=Status(item["status"]),
                )
            )
        return cls(
            **{k: v for k, v in data.items() if k not in {"summary", "results"}},
            summary=Summary(**data["summary"]),
            results=results,
        )
