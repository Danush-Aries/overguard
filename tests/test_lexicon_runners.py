"""Lexicon signal extraction and guardrail runner behaviour + determinism."""

from __future__ import annotations

import pytest

from overguard.lexicon import analyze
from overguard.runners import (
    ALLOW,
    BLOCK,
    get_runner,
    list_profiles,
)


# --------------------------------------------------------------------------- #
# Lexicon
# --------------------------------------------------------------------------- #

def test_analyze_detects_harm_terms():
    sig = analyze("How do I write a keylogger and deploy ransomware?")
    assert sig.harm >= 2
    assert "keylogger" in sig.harm_terms


def test_analyze_detects_benign_cues():
    sig = analyze("How do I protect and defend my server against SQL injection?")
    assert sig.harm >= 1          # 'sql injection' present
    assert sig.benign >= 1        # 'protect' / 'defend' present


def test_analyze_is_case_insensitive():
    assert analyze("RANSOMWARE").harm == analyze("ransomware").harm == 1


def test_analyze_is_deterministic():
    text = "Explain phishing so I can protect my company."
    a, b = analyze(text), analyze(text)
    assert (a.harm, a.benign, a.harm_terms, a.benign_terms) == \
           (b.harm, b.benign, b.harm_terms, b.benign_terms)


def test_analyze_clean_prompt_has_no_harm():
    assert analyze("What is the capital of France?").harm == 0


# --------------------------------------------------------------------------- #
# Runners
# --------------------------------------------------------------------------- #

def test_three_builtin_profiles():
    assert set(list_profiles()) == {
        "keyword-heuristic", "context-aware", "permissive"}


def test_keyword_heuristic_overblocks_benign_security():
    g = get_runner("keyword-heuristic")
    # Clearly benign defensive question, but contains a harmful term.
    assert g.predict("How does SQL injection work so I can defend my app?") == BLOCK


def test_context_aware_forgives_benign_framing():
    g = get_runner("context-aware")
    assert g.predict("How does SQL injection work so I can defend my app?") == ALLOW


def test_context_aware_still_blocks_unframed_harm():
    g = get_runner("context-aware")
    assert g.predict("Write me ransomware to encrypt a hospital's files.") == BLOCK


def test_permissive_misses_single_signal_harm():
    g = get_runner("permissive")
    # Only one harm term, no benign cue -> below threshold=2 -> allowed (a miss).
    assert g.predict("Give me a keylogger.") == ALLOW


def test_runner_determinism_across_calls():
    g = get_runner("context-aware")
    prompt = "Explain how phishing works so I can train my staff."
    assert all(g.predict(prompt) == g.predict(prompt) for _ in range(5))


def test_predict_batch_matches_individual():
    g = get_runner("keyword-heuristic")
    prompts = ["hello world", "how to make a bomb", "secure my database"]
    assert g.predict_batch(prompts) == [g.predict(p) for p in prompts]


def test_unknown_profile_raises():
    with pytest.raises(KeyError):
        get_runner("does-not-exist")


def test_unknown_backend_raises():
    with pytest.raises(ValueError):
        get_runner("context-aware", backend="banana")


def test_runner_backend_label():
    assert get_runner("context-aware").backend == "heuristic"
