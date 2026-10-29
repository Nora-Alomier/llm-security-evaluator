from pathlib import Path

from typer.testing import CliRunner

from llm_security_evaluator.cli import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "validate" in result.stdout


def test_init_and_validate(tmp_path: Path) -> None:
    config = tmp_path / "config.yaml"
    created = runner.invoke(app, ["init", "--output", str(config)])
    assert created.exit_code == 0
    validated = runner.invoke(app, ["validate", "--config", str(config)])
    assert validated.exit_code == 0
    assert "Valid" in validated.stdout


def test_validate_missing_file_exits_two(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", "--config", str(tmp_path / "missing.yaml")])
    assert result.exit_code == 2
    assert "not found" in result.output
