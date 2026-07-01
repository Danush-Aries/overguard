"""Leaderboard rendering: Markdown table + a static, self-contained HTML page.

Both views are sorted by the usefulness-preserving safety composite (desc).
No templating engine, no JS, no external assets -- a reviewer opens the HTML
straight from the committed ``results/`` directory.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Dict, List, Sequence

from .scorer import Metrics, rank

_PCT = lambda x: f"{x * 100:.1f}%"  # noqa: E731


def _medal(i: int) -> str:
    return {0: "1", 1: "2", 2: "3"}.get(i, str(i + 1))


def render_markdown(metrics: Sequence[Metrics], headline: str = "") -> str:
    """Render the leaderboard as a Markdown document."""
    ranked = rank(list(metrics))
    lines: List[str] = []
    lines.append("# OverGuard Leaderboard")
    lines.append("")
    lines.append("_Offline, CPU-first ranking of guardrail models on "
                 "**over-refusal** (false positives) vs **misses** (false "
                 "negatives)._")
    lines.append("")
    if headline:
        lines.append(f"> **Headline:** {headline}")
        lines.append("")
    lines.append("Sorted by **usefulness-preserving safety** (higher is better).")
    lines.append("")
    header = ("| # | Model | Backend | Over-refusal (FPR ↓) | Miss rate (FNR ↓) "
              "| Precision | Recall | F1 | Composite ↑ |")
    sep = "|---|-------|---------|----------------------|-------------------"\
          "|-----------|--------|----|-------------|"
    lines.append(header)
    lines.append(sep)
    for i, m in enumerate(ranked):
        lines.append(
            f"| {_medal(i)} | `{m.model}` | {m.backend} | {_PCT(m.fpr)} "
            f"| {_PCT(m.fnr)} | {m.precision:.3f} | {m.recall:.3f} "
            f"| {m.f1:.3f} | **{m.composite:.3f}** |"
        )
    lines.append("")
    lines.append(f"_{ranked[0].n_benign} benign + {ranked[0].n_harmful} harmful "
                 f"prompts. Generated "
                 f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}._")
    lines.append("")
    return "\n".join(lines)


def _row_html(i: int, m: Metrics) -> str:
    cls = "top" if i == 0 else ""
    return (
        f'<tr class="{cls}">'
        f"<td>{_medal(i)}</td>"
        f"<td class='model'>{html.escape(m.model)}</td>"
        f"<td>{html.escape(m.backend)}</td>"
        f"<td class='bad'>{_PCT(m.fpr)}</td>"
        f"<td class='bad'>{_PCT(m.fnr)}</td>"
        f"<td>{m.precision:.3f}</td>"
        f"<td>{m.recall:.3f}</td>"
        f"<td>{m.f1:.3f}</td>"
        f"<td class='score'>{m.composite:.3f}</td>"
        "</tr>"
    )


def render_html(
    metrics: Sequence[Metrics],
    headline: str = "",
    per_category: Dict[str, Dict[str, float]] | None = None,
) -> str:
    """Render a standalone HTML leaderboard page."""
    ranked = rank(list(metrics))
    rows = "\n".join(_row_html(i, m) for i, m in enumerate(ranked))
    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    cat_section = ""
    if per_category:
        blocks = []
        for model, cats in per_category.items():
            cells = "".join(
                f"<tr><td>{html.escape(c)}</td>"
                f"<td class='bad'>{_PCT(v)}</td></tr>"
                for c, v in sorted(cats.items(), key=lambda kv: -kv[1])
            )
            blocks.append(
                f"<div class='card'><h3>Over-refusal by benign category "
                f"&mdash; <code>{html.escape(model)}</code></h3>"
                f"<table class='mini'><thead><tr><th>Benign category</th>"
                f"<th>Blocked</th></tr></thead><tbody>{cells}</tbody></table></div>"
            )
        cat_section = ("<section><h2>Where the over-refusal happens</h2>"
                       + "\n".join(blocks) + "</section>")

    headline_html = (
        f"<p class='headline'>{html.escape(headline)}</p>" if headline else ""
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OverGuard Leaderboard</title>
<style>
  :root {{
    --bg:#0d1117; --panel:#161b22; --line:#30363d; --text:#e6edf3;
    --muted:#8b949e; --accent:#58a6ff; --good:#3fb950; --bad:#f85149;
  }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--text);
    font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
  .wrap {{ max-width:960px; margin:0 auto; padding:2.5rem 1.25rem 4rem; }}
  h1 {{ font-size:2rem; margin:0 0 .25rem; }}
  h1 .g {{ color:var(--accent); }}
  .sub {{ color:var(--muted); margin:0 0 1.5rem; }}
  .headline {{ background:rgba(248,81,73,.08); border:1px solid rgba(248,81,73,.35);
    border-left:4px solid var(--bad); border-radius:8px; padding:.85rem 1rem;
    margin:0 0 1.75rem; font-weight:600; }}
  table {{ width:100%; border-collapse:collapse; background:var(--panel);
    border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  th, td {{ padding:.7rem .85rem; text-align:center; border-bottom:1px solid var(--line); }}
  th {{ background:#1c2230; color:var(--muted); font-weight:600; font-size:.82rem;
    text-transform:uppercase; letter-spacing:.03em; }}
  td.model {{ text-align:left; font-family:ui-monospace,SFMono-Regular,Menlo,monospace;
    color:var(--accent); }}
  tr.top {{ background:rgba(63,185,80,.07); }}
  td.score {{ font-weight:700; color:var(--good); }}
  td.bad {{ color:var(--bad); }}
  tbody tr:last-child td {{ border-bottom:none; }}
  section {{ margin-top:2.5rem; }}
  h2 {{ font-size:1.25rem; border-bottom:1px solid var(--line); padding-bottom:.4rem; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:10px;
    padding:1rem 1.25rem; margin-top:1rem; }}
  .card h3 {{ margin:.2rem 0 .8rem; font-size:1rem; font-weight:600; }}
  table.mini {{ max-width:420px; }}
  table.mini td, table.mini th {{ text-align:left; }}
  code {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }}
  footer {{ color:var(--muted); font-size:.82rem; margin-top:2.5rem; }}
  .legend {{ color:var(--muted); font-size:.86rem; margin:.75rem 0 0; }}
</style>
</head>
<body>
<div class="wrap">
  <h1><span class="g">over</span>guard &mdash; guardrail over-refusal leaderboard</h1>
  <p class="sub">Offline &middot; CPU-first &middot; the false-positive metric
     most safety leaderboards ignore.</p>
  {headline_html}
  <table>
    <thead><tr>
      <th>#</th><th>Model</th><th>Backend</th>
      <th title="benign prompts wrongly blocked">Over-refusal<br>FPR &darr;</th>
      <th title="harmful prompts wrongly allowed">Miss rate<br>FNR &darr;</th>
      <th>Precision</th><th>Recall</th><th>F1</th>
      <th title="usefulness-preserving safety">Composite &uarr;</th>
    </tr></thead>
    <tbody>
{rows}
    </tbody>
  </table>
  <p class="legend"><strong>Composite</strong> = harmonic mean of benign-pass-rate
     (1&minus;FPR) and harmful-catch-rate (recall). A model must be safe
     <em>and</em> useful to rank well.</p>
  {cat_section}
  <footer>{ranked[0].n_benign} benign + {ranked[0].n_harmful} harmful prompts
    &middot; generated {generated} &middot; OverGuard by Dhanush Shankar.</footer>
</div>
</body>
</html>
"""
