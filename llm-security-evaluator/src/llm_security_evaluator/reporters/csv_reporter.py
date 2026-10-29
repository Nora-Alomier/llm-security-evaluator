"""Flat CSV report support."""

import csv
import json
from pathlib import Path

from ..errors import ReportError
from ..models import EvaluationRun


def write_csv(run: EvaluationRun, path: Path) -> Path:
    fields = [
        "test_id",
        "category",
        "repetition",
        "status",
        "prompt",
        "response",
        "duration_ms",
        "prompt_tokens",
        "completion_tokens",
        "failure_reasons",
        "error",
        "model",
    ]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for result in run.results:
                writer.writerow(
                    {
                        "test_id": result.test_id,
                        "category": result.category,
                        "repetition": result.repetition,
                        "status": result.status.value,
                        "prompt": result.prompt,
                        "response": result.response,
                        "duration_ms": result.duration_ms,
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "failure_reasons": json.dumps(
                            [check.reason for check in result.assertions if not check.passed],
                            ensure_ascii=False,
                        ),
                        "error": result.error,
                        "model": run.model,
                    }
                )
        return path
    except OSError as exc:
        raise ReportError(f"Could not write CSV report: {exc}") from exc
