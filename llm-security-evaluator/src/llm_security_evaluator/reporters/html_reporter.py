"""Self-contained, offline HTML report."""

from collections import defaultdict
from html import escape
from pathlib import Path

from ..errors import ReportError
from ..models import EvaluationRun


def write_html(run: EvaluationRun, path: Path) -> Path:
    grouped = defaultdict(list)
    for result in run.results:
        grouped[result.category].append(result)
    sections = []
    for category, results in sorted(grouped.items()):
        cards = []
        for result in results:
            reasons = [check.reason for check in result.assertions if not check.passed]
            reason_html = "".join(f"<li>{escape(reason)}</li>" for reason in reasons)
            if result.error:
                reason_html += f"<li>{escape(result.error)}</li>"
            cards.append(
                f"""
                <article class="result {result.status.value.lower()}">
                  <header><span class="badge">{result.status.value}</span>
                    <strong>{escape(result.test_id)}</strong><span>Run {result.repetition}</span>
                    <span>{result.duration_ms:.2f} ms</span></header>
                  <details><summary>Prompt and response</summary>
                    <h4>Prompt</h4><pre>{escape(result.prompt)}</pre>
                    <h4>Response</h4><pre>{escape(result.response) or "(empty)"}</pre>
                    {f"<h4>Failure details</h4><ul>{reason_html}</ul>" if reason_html else ""}
                  </details>
                </article>"""
            )
        sections.append(f"<section><h2>{escape(category)}</h2>{''.join(cards)}</section>")

    score = run.summary.pass_rate
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(run.name)} — LLM Security Report</title>
<style>
:root{{--bg:#0b1020;--panel:#141b2d;--text:#e8ecf6;--muted:#9ca9c4;--pass:#38d996;--fail:#ff6b7a;--error:#ffbf69;--line:#29334c}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 system-ui,sans-serif}}
main{{max-width:1100px;margin:auto;padding:42px 20px}}h1{{font-size:2.1rem;margin-bottom:4px}}h2{{margin-top:38px}}
.muted,header span{{color:var(--muted)}}.summary{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:14px;margin:28px 0}}
.metric,.result,.meta{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px}}
.metric strong{{display:block;font-size:1.7rem}}.score strong{{color:var(--pass)}}.result{{margin:10px 0;border-left:5px solid}}
.result.pass{{border-left-color:var(--pass)}}.result.fail{{border-left-color:var(--fail)}}.result.error{{border-left-color:var(--error)}}
.result header{{display:flex;gap:14px;align-items:center;flex-wrap:wrap}}.result header strong{{margin-right:auto}}
.badge{{font-size:.75rem;font-weight:800;padding:3px 8px;border-radius:999px;background:#25304a;color:var(--text)}}
details{{margin-top:13px}}summary{{cursor:pointer;color:#b9c9ff}}pre{{white-space:pre-wrap;word-break:break-word;background:#090d18;padding:13px;border-radius:8px;color:#dfe7fa}}
.meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:7px}}a{{color:#9db4ff}}
</style></head><body><main>
<p class="muted">LLM Security Evaluator</p><h1>{escape(run.name)}</h1>
<p class="muted">Deterministic assertions are evaluation signals, not proof of comprehensive model safety.</p>
<div class="summary"><div class="metric score"><span>Security score</span><strong>{score:.2f}%</strong></div>
<div class="metric"><span>Total</span><strong>{run.summary.total}</strong></div><div class="metric"><span>Passed</span><strong>{run.summary.passed}</strong></div>
<div class="metric"><span>Failed</span><strong>{run.summary.failed}</strong></div><div class="metric"><span>Errors</span><strong>{run.summary.errors}</strong></div></div>
<div class="meta"><div><strong>Model</strong><br>{escape(run.model)}</div><div><strong>Provider</strong><br>{escape(run.provider)}</div>
<div><strong>Started</strong><br>{escape(run.started_at)}</div><div><strong>Completed</strong><br>{escape(run.completed_at)}</div></div>
{"".join(sections)}
<p class="muted">Generated locally by LLM Security Evaluator {escape(run.tool_version)}. No external assets.</p>
</main></body></html>"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return path
    except OSError as exc:
        raise ReportError(f"Could not write HTML report: {exc}") from exc
