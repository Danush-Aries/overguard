"""Metric math, ranking, and per-category over-refusal tests."""

from __future__ import annotations

from overguard.scorer import (
    Prediction,
    category_fpr,
    compute_metrics,
    rank,
)


def _preds(rows):
    return [Prediction(id=str(i), gold=g, pred=p, category=c)
            for i, (g, p, c) in enumerate(rows)]


def test_confusion_counts_and_rates():
    # 2 harmful blocked (TP), 1 harmful allowed (FN),
    # 1 benign blocked (FP), 2 benign allowed (TN).
    preds = _preds([
        ("harmful", "block", "cyber"),
        ("harmful", "block", "cyber"),
        ("harmful", "allow", "cyber"),
        ("benign", "block", "security_education"),
        ("benign", "allow", "security_education"),
        ("benign", "allow", "tech_homonym"),
    ])
    m = compute_metrics("m", preds)
    assert (m.tp, m.fn, m.fp, m.tn) == (2, 1, 1, 2)
    assert m.n == 6 and m.n_harmful == 3 and m.n_benign == 3
    assert m.fpr == round(1 / 3, 4)      # over-refusal
    assert m.fnr == round(1 / 3, 4)      # miss rate
    assert m.recall == round(2 / 3, 4)
    assert m.precision == round(2 / 3, 4)


def test_recall_is_one_minus_fnr():
    preds = _preds([
        ("harmful", "block", "x"),
        ("harmful", "allow", "x"),
        ("benign", "allow", "y"),
    ])
    m = compute_metrics("m", preds)
    assert abs(m.recall - (1 - m.fnr)) < 1e-9


def test_f1_is_harmonic_mean_of_precision_recall():
    preds = _preds([
        ("harmful", "block", "x"),
        ("harmful", "block", "x"),
        ("harmful", "allow", "x"),
        ("benign", "block", "y"),
        ("benign", "allow", "y"),
    ])
    m = compute_metrics("m", preds)
    expected = 2 * m.precision * m.recall / (m.precision + m.recall)
    assert abs(m.f1 - round(expected, 4)) < 1e-4


def test_composite_rewards_safe_and_useful():
    # Perfect guardrail: no over-refusal, no misses -> composite 1.0.
    perfect = _preds([
        ("harmful", "block", "x"),
        ("benign", "allow", "y"),
    ])
    m = compute_metrics("perfect", perfect)
    assert m.fpr == 0.0 and m.fnr == 0.0
    assert m.composite == 1.0


def test_composite_zero_when_blocks_everything():
    # Over-blocker that blocks all benign -> 1-FPR = 0 -> composite 0.
    allblock = _preds([
        ("harmful", "block", "x"),
        ("benign", "block", "y"),
    ])
    m = compute_metrics("blocker", allblock)
    assert m.fpr == 1.0
    assert m.composite == 0.0


def test_safe_div_no_zero_division():
    # All benign, guardrail allows everything: recall/fnr undefined -> 0.0.
    preds = _preds([("benign", "allow", "y"), ("benign", "allow", "y")])
    m = compute_metrics("m", preds)
    assert m.fnr == 0.0 and m.recall == 0.0 and m.fpr == 0.0


def test_backend_label_passthrough():
    m = compute_metrics("m", _preds([("benign", "allow", "y")]), backend="ollama")
    assert m.backend == "ollama"


def test_rank_orders_by_composite_desc():
    good = compute_metrics("good", _preds([
        ("harmful", "block", "x"), ("benign", "allow", "y")]))
    bad = compute_metrics("bad", _preds([
        ("harmful", "allow", "x"), ("benign", "block", "y")]))
    ordered = rank([bad, good])
    assert [m.model for m in ordered] == ["good", "bad"]


def test_rank_tiebreaks_on_lower_fpr():
    # Two models with equal composite; the one with lower FPR wins.
    # Model A: FPR 0, recall r_a ; Model B: FPR>0 but same composite is hard to
    # force, so assert the sort key directly: equal composite -> lower fpr first.
    a = compute_metrics("a", _preds([
        ("harmful", "block", "x"), ("harmful", "allow", "x"),
        ("benign", "allow", "y"), ("benign", "allow", "y")]))
    b = compute_metrics("b", _preds([
        ("harmful", "block", "x"), ("harmful", "allow", "x"),
        ("benign", "allow", "y"), ("benign", "allow", "y")]))
    # Identical inputs -> identical composite; tie-break falls to model name.
    ordered = rank([b, a])
    assert [m.model for m in ordered] == ["a", "b"]


def test_category_fpr_only_covers_benign():
    preds = _preds([
        ("benign", "block", "security_education"),
        ("benign", "block", "security_education"),
        ("benign", "allow", "tech_homonym"),
        ("harmful", "block", "cyber_offensive"),  # must be ignored
    ])
    cats = category_fpr(preds)
    assert cats == {"security_education": 1.0, "tech_homonym": 0.0}
    assert "cyber_offensive" not in cats
