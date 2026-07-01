"""Reporter rendering and end-to-end CLI smoke tests."""

from __future__ import annotations

import json

from overguard.cli import main
from overguard.reporter import render_html, render_markdown
from overguard.scorer import Prediction, compute_metrics


def _sample_metrics():
    good = compute_metrics("context-aware", [
        Prediction("1", "harmful", "block", "cyber"),
        Prediction("2", "benign", "allow", "security_education"),
    ])
    bad = compute_metrics("keyword-heuristic", [
        Prediction("3", "harmful", "block", "cyber"),
        Prediction("4", "benign", "block", "security_education"),
    ])
    return [bad, good]


def test_markdown_has_table_and_headline():
    md = render_markdown(_sample_metrics(), headline="over-refusal is real")
    assert "# OverGuard Leaderboard" in md
    assert "over-refusal is real" in md
    assert "| # | Model |" in md
    # Ranked: context-aware (composite 1.0) should appear before keyword-heuristic.
    assert md.index("context-aware") < md.index("keyword-heuristic")


def test_html_is_self_contained():
    html = render_html(_sample_metrics(), headline="finding",
                       per_category={"keyword-heuristic": {"security_education": 1.0}})
    assert html.startswith("<!DOCTYPE html>")
    assert "<style>" in html          # inline CSS, no external assets
    assert "finding" in html
    assert "Over-refusal" in html
    assert "security_education" in html


def test_html_escapes_content():
    m = compute_metrics("<script>", [Prediction("1", "benign", "allow", "x")])
    html = render_html([m])
    assert "<script>" not in html.split("<style>")[1]  # escaped in body table


def test_cli_run_writes_artifacts(tmp_path, capsys):
    rc = main(["run", "--results", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / "metrics.json").exists()
    assert (tmp_path / "leaderboard.html").exists()
    assert (tmp_path / "leaderboard.md").exists()
    summary = json.loads((tmp_path / "metrics.json").read_text())
    # Winner of the composite ranking is context-aware.
    assert summary["metrics"][0]["model"] == "context-aware"
    assert summary["dataset"]["total"] == 240
    # Per-model prediction dumps exist.
    assert (tmp_path / "context-aware" / "predictions.jsonl").exists()


def test_cli_run_single_model(tmp_path):
    rc = main(["run", "--model", "permissive", "--results", str(tmp_path)])
    assert rc == 0
    summary = json.loads((tmp_path / "metrics.json").read_text())
    assert [m["model"] for m in summary["metrics"]] == ["permissive"]


def test_cli_headline_and_leaderboard(tmp_path, capsys):
    main(["run", "--results", str(tmp_path)])
    capsys.readouterr()
    assert main(["headline", "--results", str(tmp_path)]) == 0
    assert "security" in capsys.readouterr().out.lower()
    assert main(["leaderboard", "--results", str(tmp_path)]) == 0


def test_cli_models_lists_profiles(capsys):
    assert main(["models"]) == 0
    out = capsys.readouterr().out
    for name in ("keyword-heuristic", "context-aware", "permissive"):
        assert name in out


def test_cli_leaderboard_without_results_errors(tmp_path):
    assert main(["leaderboard", "--results", str(tmp_path / "empty")]) == 1
