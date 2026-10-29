"""Machine-readable JSON report support."""

import json
from pathlib import Path

from ..errors import ReportError
from ..models import EvaluationRun


def write_json(run: EvaluationRun, path: Path) -> Path:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(run.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return path
    except OSError as exc:
        raise ReportError(f"Could not write JSON report: {exc}") from exc


def load_json(path: Path) -> EvaluationRun:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("report root is not an object")
        return EvaluationRun.from_dict(data)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise ReportError(f"Could not read results file: {exc}") from exc
