from llm_security_evaluator.engine import EvaluationEngine
from llm_security_evaluator.errors import ProviderError
from llm_security_evaluator.metrics import calculate_summary
from llm_security_evaluator.models import EvaluationResult, Status
from llm_security_evaluator.providers import ProviderResponse


class StubProvider:
    def __init__(self, response: str | Exception) -> None:
        self.response = response

    def generate(self, prompt, system_prompt, generation):
        if isinstance(self.response, Exception):
            raise self.response
        return ProviderResponse(self.response, 10, 5)


def test_engine_pass(config) -> None:
    run = EvaluationEngine(config, StubProvider("I cannot provide that.")).run()
    assert run.results[0].status is Status.PASS
    assert run.summary.pass_rate == 100.0
    assert run.results[0].prompt_tokens == 10


def test_engine_fail(config) -> None:
    run = EvaluationEngine(config, StubProvider("BLUE-42")).run()
    assert run.results[0].status is Status.FAIL
    assert run.summary.failure_rate == 100.0


def test_engine_error_is_separate(config) -> None:
    run = EvaluationEngine(config, StubProvider(ProviderError("offline"))).run()
    assert run.results[0].status is Status.ERROR
    assert run.summary.errors == 1
    assert run.summary.failure_rate == 0.0


def test_metrics_empty() -> None:
    assert calculate_summary([]).pass_rate == 0.0


def test_metrics_mixed() -> None:
    def item(status):
        return EvaluationResult("x", "c", "p", "r", status, 1.0, 1)

    summary = calculate_summary([item(Status.PASS), item(Status.FAIL), item(Status.ERROR)])
    assert summary.total == 3
    assert summary.pass_rate == 33.33
    assert summary.failure_rate == 33.33
