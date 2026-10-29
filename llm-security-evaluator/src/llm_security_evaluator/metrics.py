"""Summary metric calculations."""

from .models import EvaluationResult, Status, Summary


def calculate_summary(results: list[EvaluationResult]) -> Summary:
    total = len(results)
    passed = sum(result.status is Status.PASS for result in results)
    failed = sum(result.status is Status.FAIL for result in results)
    errors = sum(result.status is Status.ERROR for result in results)
    return Summary(
        total=total,
        passed=passed,
        failed=failed,
        errors=errors,
        pass_rate=round((passed / total * 100) if total else 0.0, 2),
        failure_rate=round((failed / total * 100) if total else 0.0, 2),
    )
