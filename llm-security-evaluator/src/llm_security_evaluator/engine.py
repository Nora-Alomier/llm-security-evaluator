"""Configuration-driven evaluation engine."""

from __future__ import annotations

from time import perf_counter
from typing import Protocol

from .assertions import evaluate_assertions
from .errors import ProviderError
from .metrics import calculate_summary
from .models import EvaluationConfig, EvaluationResult, EvaluationRun, GenerationConfig, Status
from .providers import ProviderResponse


class Provider(Protocol):
    def generate(
        self, prompt: str, system_prompt: str, generation: GenerationConfig
    ) -> ProviderResponse: ...


class EvaluationEngine:
    def __init__(self, config: EvaluationConfig, provider: Provider) -> None:
        self.config = config
        self.provider = provider

    def run(self) -> EvaluationRun:
        started_at = EvaluationRun.now_iso()
        results: list[EvaluationResult] = []
        for test in self.config.tests:
            repetitions = test.repetitions or self.config.repetitions
            for repetition in range(1, repetitions + 1):
                began = perf_counter()
                try:
                    response = self.provider.generate(
                        test.prompt,
                        test.system_prompt or self.config.system_prompt,
                        self.config.generation,
                    )
                    checks = evaluate_assertions(response.text, test.assertions)
                    status = Status.PASS if all(check.passed for check in checks) else Status.FAIL
                    results.append(
                        EvaluationResult(
                            test_id=test.id,
                            category=test.category,
                            prompt=test.prompt,
                            response=response.text,
                            status=status,
                            duration_ms=round((perf_counter() - began) * 1000, 2),
                            repetition=repetition,
                            assertions=checks,
                            prompt_tokens=response.prompt_tokens,
                            completion_tokens=response.completion_tokens,
                            metadata=response.metadata,
                        )
                    )
                except ProviderError as exc:
                    results.append(
                        EvaluationResult(
                            test_id=test.id,
                            category=test.category,
                            prompt=test.prompt,
                            response="",
                            status=Status.ERROR,
                            duration_ms=round((perf_counter() - began) * 1000, 2),
                            repetition=repetition,
                            error=str(exc),
                        )
                    )
        return EvaluationRun(
            name=self.config.name,
            model=self.config.provider.model,
            provider=self.config.provider.name,
            endpoint=self.config.provider.endpoint,
            started_at=started_at,
            completed_at=EvaluationRun.now_iso(),
            generation={
                "temperature": self.config.generation.temperature,
                "max_tokens": self.config.generation.max_tokens,
                "seed": self.config.generation.seed,
            },
            summary=calculate_summary(results),
            results=results,
        )
