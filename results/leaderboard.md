# OverGuard Leaderboard

_Offline, CPU-first ranking of guardrail models on **over-refusal** (false positives) vs **misses** (false negatives)._

> **Headline:** The `keyword-heuristic` guardrail over-blocks 100% of benign security questions (overall over-refusal 48%), while `context-aware` preserves them and still catches 72% of genuinely harmful prompts.

Sorted by **usefulness-preserving safety** (higher is better).

| # | Model | Backend | Over-refusal (FPR ↓) | Miss rate (FNR ↓) | Precision | Recall | F1 | Composite ↑ |
|---|-------|---------|----------------------|-------------------|-----------|--------|----|-------------|
| 1 | `context-aware` | heuristic | 5.0% | 27.5% | 0.935 | 0.725 | 0.817 | **0.822** |
| 2 | `keyword-heuristic` | heuristic | 47.5% | 21.7% | 0.623 | 0.783 | 0.694 | **0.629** |
| 3 | `permissive` | heuristic | 0.8% | 76.7% | 0.966 | 0.233 | 0.376 | **0.378** |

_120 benign + 120 harmful prompts. Generated 2026-07-01 21:09 UTC._
