import csv
from pathlib import Path

from llm_security_evaluator.reporters import load_json, write_csv, write_html, write_json


def test_json_round_trip(tmp_path: Path, sample_run) -> None:
    path = write_json(sample_run, tmp_path / "result.json")
    loaded = load_json(path)
    assert loaded.model == "llama3.2"
    assert loaded.results[0].status.value == "PASS"


def test_csv_report(tmp_path: Path, sample_run) -> None:
    path = write_csv(sample_run, tmp_path / "result.csv")
    with path.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["test_id"] == "t1"
    assert rows[0]["status"] == "PASS"


def test_html_report_is_self_contained_and_escaped(tmp_path: Path, sample_run) -> None:
    sample_run.results[0].response = "<script>alert(1)</script>"
    text = write_html(sample_run, tmp_path / "result.html").read_text(encoding="utf-8")
    assert "<!doctype html>" in text
    assert "&lt;script&gt;" in text
    assert "https://" not in text
