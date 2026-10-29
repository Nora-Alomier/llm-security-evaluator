"""Professional Typer command-line interface."""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .config import load_config, validate_local_endpoint
from .engine import EvaluationEngine
from .errors import LLMSECError
from .models import ProviderConfig
from .providers import OllamaProvider
from .reporters import load_json, write_csv, write_html, write_json

app = typer.Typer(
    name="llmsec",
    help="Evaluate local LLM security boundaries with reproducible test cases.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)
EXAMPLE = Path(__file__).parents[2] / "examples" / "banking-assistant.yaml"


def _fail(exc: Exception, code: int = 2) -> None:
    err_console.print(f"[bold red]Error:[/bold red] {exc}")
    raise typer.Exit(code)


@app.command()
def init(
    output: Annotated[Path, typer.Option("--output", "-o", help="New configuration path.")] = Path(
        "llmsec.yaml"
    ),
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
) -> None:
    """Create a documented, safe example configuration."""
    if output.exists() and not force:
        _fail(f"File already exists: {output}. Use --force to overwrite.")
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        if EXAMPLE.is_file():
            template = EXAMPLE.read_text(encoding="utf-8")
        else:
            template = (
                resources.files("llm_security_evaluator")
                .joinpath("data/banking-assistant.yaml")
                .read_text(encoding="utf-8")
            )
        output.write_text(template, encoding="utf-8")
    except OSError as exc:
        _fail(f"Could not create configuration: {exc}")
    console.print(f"[green]Created[/green] {output}")


@app.command()
def validate(
    config: Annotated[Path, typer.Option("--config", "-c", help="YAML or JSON configuration.")],
) -> None:
    """Validate a configuration without contacting Ollama."""
    try:
        parsed = load_config(config)
    except LLMSECError as exc:
        _fail(exc)
    message = (
        f"[green]Valid[/green] — {len(parsed.tests)} tests, "
        f"model [bold]{parsed.provider.model}[/bold]"
    )
    console.print(message)


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c", help="YAML or JSON configuration.")],
) -> None:
    """Execute all configured evaluations and write local reports."""
    try:
        parsed = load_config(config)
        with OllamaProvider(parsed.provider) as provider:
            console.print(
                f"Evaluating [bold]{parsed.provider.model}[/bold] with {len(parsed.tests)} cases…"
            )
            result = EvaluationEngine(parsed, provider).run()
        output_dir = (config.parent / parsed.output.directory).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        writers = {"json": write_json, "csv": write_csv, "html": write_html}
        for format_name in parsed.output.formats:
            path = writers[format_name](result, output_dir / f"results.{format_name}")
            console.print(f"[green]Wrote[/green] {path}")
    except LLMSECError as exc:
        _fail(exc)
    _summary_table(result)
    if result.summary.errors:
        raise typer.Exit(2)
    if result.summary.failed:
        raise typer.Exit(1)


@app.command()
def report(
    input_path: Annotated[Path, typer.Option("--input", "-i", help="Existing JSON results.")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Report output directory.")
    ] = None,
    formats: Annotated[str, typer.Option(help="Comma-separated: json,csv,html.")] = "html,csv",
) -> None:
    """Generate reports from an existing JSON result file."""
    try:
        run_data = load_json(input_path)
        destination = output or input_path.parent
        selected = [value.strip().lower() for value in formats.split(",") if value.strip()]
        writers = {"json": write_json, "csv": write_csv, "html": write_html}
        invalid = set(selected) - set(writers)
        if not selected or invalid:
            _fail(f"Invalid report formats: {sorted(invalid)}")
        for name in selected:
            path = writers[name](run_data, destination / f"results.{name}")
            console.print(f"[green]Wrote[/green] {path}")
    except LLMSECError as exc:
        _fail(exc)


@app.command()
def models(
    endpoint: Annotated[
        str, typer.Option(help="Local Ollama endpoint.")
    ] = "http://localhost:11434",
) -> None:
    """List models installed in the local Ollama instance."""
    try:
        validate_local_endpoint(endpoint)
        with OllamaProvider(ProviderConfig(endpoint=endpoint)) as provider:
            names = provider.list_models()
    except LLMSECError as exc:
        _fail(exc)
    if not names:
        console.print("No local Ollama models found.")
        return
    for name in names:
        console.print(f"• {name}")


def _summary_table(result: object) -> None:
    summary = result.summary
    table = Table(title="Evaluation summary")
    for column in ("Total", "Passed", "Failed", "Errors", "Pass rate"):
        table.add_column(column)
    table.add_row(
        str(summary.total),
        str(summary.passed),
        str(summary.failed),
        str(summary.errors),
        f"{summary.pass_rate:.2f}%",
    )
    console.print(table)


if __name__ == "__main__":
    app()
