"""OverGuard command-line interface.

    overguard run [--model M ...] [--backend heuristic|ollama|hf]
    overguard leaderboard
    overguard models
    overguard headline

`run` evaluates guardrail models against the vendored dataset, writes raw
predictions + metrics under ``results/``, and prints a terminal leaderboard.
`leaderboard` re-renders ``leaderboard.html`` / ``leaderboard.md`` from the
saved metrics. Everything works offline with zero downloads by default.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Sequence

from . import __version__
from .datasets import dataset_stats, load_dataset
from .reporter import render_html, render_markdown
from .runners import get_runner, list_profiles
from .scorer import Metrics, Prediction, category_fpr, compute_metrics, rank

DEFAULT_RESULTS = Path("results")
DEFAULT_MODELS = list_profiles()  # all three built-in profiles


# --------------------------------------------------------------------------- #
# Pretty printing (rich if available, plain fallback otherwise).
# --------------------------------------------------------------------------- #

def _print_table(metrics: Sequence[Metrics], headline: str = "") -> None:
    ranked = rank(list(metrics))
    try:
        from rich.console import Console
        from rich.table import Table
        from rich import box

        console = Console()
        console.print()
        console.print("[bold cyan]overguard[/] — guardrail over-refusal leaderboard",
                      justify="left")
        if headline:
            console.print(f"[bold yellow]▶ {headline}[/]")
        table = Table(box=box.ROUNDED, header_style="bold")
        table.add_column("#", justify="right")
        table.add_column("Model", style="cyan")
        table.add_column("Backend")
        table.add_column("Over-refusal\nFPR ↓", justify="right", style="red")
        table.add_column("Miss\nFNR ↓", justify="right", style="red")
        table.add_column("Prec", justify="right")
        table.add_column("Recall", justify="right")
        table.add_column("F1", justify="right")
        table.add_column("Composite ↑", justify="right", style="bold green")
        for i, m in enumerate(ranked):
            table.add_row(
                str(i + 1), m.model, m.backend,
                f"{m.fpr*100:.1f}%", f"{m.fnr*100:.1f}%",
                f"{m.precision:.3f}", f"{m.recall:.3f}", f"{m.f1:.3f}",
                f"{m.composite:.3f}",
            )
        console.print(table)
        console.print()
    except ImportError:
        # Plain-text fallback keeps the CLI usable without rich installed.
        print("\noverguard — guardrail over-refusal leaderboard")
        if headline:
            print(f">> {headline}")
        hdr = f"{'#':>2} {'Model':<18} {'FPR':>7} {'FNR':>7} {'Prec':>6} {'Rec':>6} {'F1':>6} {'Comp':>6}"
        print(hdr)
        print("-" * len(hdr))
        for i, m in enumerate(ranked):
            print(f"{i+1:>2} {m.model:<18} {m.fpr*100:>6.1f}% {m.fnr*100:>6.1f}% "
                  f"{m.precision:>6.3f} {m.recall:>6.3f} {m.f1:>6.3f} {m.composite:>6.3f}")
        print()


# --------------------------------------------------------------------------- #
# Core evaluation.
# --------------------------------------------------------------------------- #

def evaluate(models: List[str], backend: str, results_dir: Path) -> Dict[str, object]:
    """Run models over the dataset, write artifacts, return the summary dict."""
    prompts = load_dataset()
    stats = dataset_stats(prompts)
    results_dir.mkdir(parents=True, exist_ok=True)

    all_metrics: List[Metrics] = []
    per_category: Dict[str, Dict[str, float]] = {}

    for model_id in models:
        runner = get_runner(model_id, backend=backend)
        preds: List[Prediction] = []
        raw_rows = []
        for p in prompts:
            decision = runner.predict(p.prompt)
            preds.append(Prediction(id=p.id, gold=p.label, pred=decision,
                                     category=p.category))
            raw_rows.append({
                "id": p.id, "category": p.category, "gold": p.label,
                "prediction": decision, "prompt": p.prompt,
            })

        metrics = compute_metrics(runner.name, preds, backend=runner.backend)
        all_metrics.append(metrics)
        per_category[runner.name] = category_fpr(preds)

        model_dir = results_dir / runner.name.replace(":", "_").replace("/", "_")
        model_dir.mkdir(parents=True, exist_ok=True)
        with (model_dir / "predictions.jsonl").open("w", encoding="utf-8") as f:
            for row in raw_rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        with (model_dir / "metrics.json").open("w", encoding="utf-8") as f:
            json.dump(metrics.as_dict(), f, indent=2)

    ranked = rank(all_metrics)
    headline = build_headline(ranked, per_category)

    summary = {
        "dataset": stats,
        "backend": backend,
        "metrics": [m.as_dict() for m in ranked],
        "per_category_fpr": per_category,
        "headline": headline,
    }
    with (results_dir / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    _write_leaderboard(summary, results_dir)
    return summary


def build_headline(ranked: Sequence[Metrics],
                   per_category: Dict[str, Dict[str, float]]) -> str:
    """Craft the defensible headline finding from the worst over-blocker."""
    if not ranked:
        return ""
    # The most over-refusing model = highest FPR.
    worst = max(ranked, key=lambda m: m.fpr)
    cats = per_category.get(worst.model, {})
    sec = cats.get("security_education")
    best = ranked[0]  # ranked is sorted by composite desc
    if sec is not None:
        return (f"The `{worst.model}` guardrail over-blocks "
                f"{sec*100:.0f}% of benign security questions "
                f"(overall over-refusal {worst.fpr*100:.0f}%), while "
                f"`{best.model}` preserves them and still catches "
                f"{best.recall*100:.0f}% of genuinely harmful prompts.")
    return (f"`{worst.model}` over-refuses {worst.fpr*100:.0f}% of benign "
            f"prompts; `{best.model}` leads the usefulness-preserving safety "
            f"ranking at composite {best.composite:.3f}.")


def _write_leaderboard(summary: Dict[str, object], results_dir: Path) -> None:
    metrics = [Metrics(**m) for m in summary["metrics"]]
    headline = str(summary.get("headline", ""))
    per_cat = summary.get("per_category_fpr")  # type: ignore[assignment]
    (results_dir / "leaderboard.md").write_text(
        render_markdown(metrics, headline), encoding="utf-8")
    (results_dir / "leaderboard.html").write_text(
        render_html(metrics, headline, per_cat), encoding="utf-8")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# Subcommands.
# --------------------------------------------------------------------------- #

def cmd_run(args: argparse.Namespace) -> int:
    models = args.model or DEFAULT_MODELS
    results_dir = Path(args.results)
    print(f"Evaluating {len(models)} model(s) via '{args.backend}' backend: "
          f"{', '.join(models)}")
    summary = evaluate(models, args.backend, results_dir)
    metrics = [Metrics(**m) for m in summary["metrics"]]
    _print_table(metrics, str(summary["headline"]))
    print(f"Wrote predictions + metrics to {results_dir}/")
    print(f"Wrote {results_dir}/leaderboard.html and leaderboard.md")
    return 0


def cmd_leaderboard(args: argparse.Namespace) -> int:
    results_dir = Path(args.results)
    summary_path = results_dir / "metrics.json"
    if not summary_path.exists():
        print(f"No results found at {summary_path}. Run `overguard run` first.",
              file=sys.stderr)
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    _write_leaderboard(summary, results_dir)
    metrics = [Metrics(**m) for m in summary["metrics"]]
    _print_table(metrics, str(summary.get("headline", "")))
    print(f"Rendered {results_dir}/leaderboard.html and leaderboard.md")
    return 0


def cmd_models(args: argparse.Namespace) -> int:
    print("Built-in heuristic profiles (zero-download, default backend):")
    for name in list_profiles():
        runner = get_runner(name)
        print(f"  - {name}: {runner.description}")
    print("\nOptional real backends (gated behind --backend):")
    print("  --backend ollama <model>   e.g. llama-guard3, granite3-guardian")
    print("  --backend hf <model>       e.g. meta-llama/Prompt-Guard-86M")
    return 0


def cmd_headline(args: argparse.Namespace) -> int:
    results_dir = Path(args.results)
    summary_path = results_dir / "metrics.json"
    if not summary_path.exists():
        print("No results yet. Run `overguard run` first.", file=sys.stderr)
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    print(summary.get("headline", ""))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="overguard",
        description="Offline, CPU-first leaderboard for guardrail over-refusal.")
    p.add_argument("--version", action="version",
                   version=f"overguard {__version__}")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="evaluate guardrail models on the dataset")
    run.add_argument("--model", action="append",
                     help="model/profile id (repeatable; default = all profiles)")
    run.add_argument("--backend", default="heuristic",
                     choices=["heuristic", "ollama", "hf"],
                     help="runner backend (default: heuristic, zero-download)")
    run.add_argument("--results", default=str(DEFAULT_RESULTS),
                     help="output directory (default: results/)")
    run.set_defaults(func=cmd_run)

    lb = sub.add_parser("leaderboard", help="render leaderboard from saved results")
    lb.add_argument("--results", default=str(DEFAULT_RESULTS))
    lb.set_defaults(func=cmd_leaderboard)

    md = sub.add_parser("models", help="list available models/profiles")
    md.set_defaults(func=cmd_models)

    hl = sub.add_parser("headline", help="print the headline finding")
    hl.add_argument("--results", default=str(DEFAULT_RESULTS))
    hl.set_defaults(func=cmd_headline)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
