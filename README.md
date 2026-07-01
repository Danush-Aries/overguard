# overguard

**An offline, CPU-first leaderboard that ranks guardrail models on
over-refusal — how often they wrongly block *benign* prompts — alongside their
miss rate on genuinely harmful ones.**

No API keys. No downloads. No GPU. `pip install -e .` and `overguard run`
reproduces the whole leaderboard in a couple of seconds on a laptop.

---

## Why over-refusal matters

Most safety leaderboards ask one question: *does the guardrail catch harmful
prompts?* They reward blocking. But a guardrail that blocks everything scores
perfectly on that axis while being **useless** — it also blocks the security
engineer asking *"how does SQL injection work so I can defend my app?"*, the
developer running `kill` on a stuck process, and the nurse asking about a drug
overdose *symptom*.

That failure — **benign prompts wrongly blocked** — is **over-refusal**, and it
is the false-positive rate that safety benchmarks routinely ignore. It is the
difference between a guardrail people trust and one they rip out because it
keeps getting in the way.

OverGuard makes over-refusal the headline metric, and scores guardrails on
whether they are safe **and** useful — not just safe.

## The leaderboard

_Offline heuristic backend · 120 benign + 120 harmful prompts · sorted by
usefulness-preserving safety (higher is better)._

| # | Model | Over-refusal (FPR ↓) | Miss rate (FNR ↓) | Precision | Recall | F1 | Composite ↑ |
|---|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | `context-aware`      |  5.0% | 27.5% | 0.935 | 0.725 | 0.817 | **0.822** |
| 2 | `keyword-heuristic`  | 47.5% | 21.7% | 0.623 | 0.783 | 0.694 | **0.629** |
| 3 | `permissive`         |  0.8% | 76.7% | 0.966 | 0.233 | 0.376 | **0.378** |

> **Headline finding:** the `keyword-heuristic` guardrail over-blocks **100% of
> benign security questions** (overall over-refusal 48%), while `context-aware`
> preserves them and still catches **72%** of genuinely harmful prompts.

The static HTML view (dark theme, per-category over-refusal breakdown) is
committed at [`results/leaderboard.html`](results/leaderboard.html) — open it
straight from the repo, no server needed.

## What the ranking shows

- **`context-aware` wins** because it forgives clear defensive/educational
  framing: it blocks a scary topic *only* when there is no benign cue. Low
  over-refusal (5%) **and** solid harm-catching (72%).
- **`keyword-heuristic` is the cautionary tale.** It blocks on any risky
  keyword, blind to intent, so it over-refuses nearly half of all benign
  prompts and **every** benign security question. High recall does not save it.
- **`permissive` ranks last** despite the *lowest* over-refusal (0.8%): it only
  blocks on strong multi-signal harm, so it misses 77% of harmful prompts. The
  composite punishes it — being harmless-looking is not the same as being safe.

The composite is the harmonic mean of **benign-pass-rate (1 − FPR)** and
**harmful-catch-rate (recall)**: a guardrail must do *both* well to rank high.
Over-blocking or under-blocking each tanks the score.

## Quickstart

```bash
pip install -e .        # only dependency: rich (pretty terminal tables)
overguard run           # evaluate all profiles, write results/, print the board
overguard leaderboard   # re-render results/leaderboard.html + .md from saved metrics
```

Other commands:

```bash
overguard models        # list the built-in guardrail profiles
overguard headline      # print just the headline finding
```

Run the tests:

```bash
pip install -e ".[dev]"
pytest                  # 40 tests: metric math, ranking, dataset integrity, runners, CLI
```

## Methodology

**Framing.** Positive class = *harmful* (guardrail should `block`). So:

- **False Positive** = benign prompt **blocked** → *over-refusal* (the metric we
  center).
- **False Negative** = harmful prompt **allowed** → *miss*.

**The guardrail "models".** The default backend is three transparent,
deterministic lexical guardrails that share one signal extractor and differ
only in their **decision policy** — which is exactly the axis this benchmark
studies:

| Profile | Policy | Real-world analogue |
|---------|--------|---------------------|
| `keyword-heuristic` | Block on any risky keyword, ignore framing | Over-tuned pattern classifier |
| `context-aware`     | Block risky topics but forgive clear benign/defensive framing | Well-tuned guardrail (Llama-Guard-3 class) |
| `permissive`        | Block only on strong multi-signal harm | Under-tuned small model (Prompt-Guard class) |

**Metrics** (`overguard/scorer.py`) are hand-rolled, no scikit-learn, fully
deterministic: FPR, FNR, precision, recall, F1, accuracy, and the composite.
Per-category over-refusal (`category_fpr`) powers the headline.

**Dataset** — 240 committed prompts (120 benign + 120 harmful across 11
categories). Provenance, category breakdown, and attribution to the public work
that inspired the methodology (XSTest, OR-Bench, WildGuardMix) are in
[`DATA.md`](DATA.md).

**Optional real backends.** Thin adapters for local guardrail models are
included but gated behind a flag so the default path stays offline:

```bash
overguard run --backend ollama --model llama-guard3
overguard run --backend hf --model meta-llama/Prompt-Guard-86M   # needs overguard[real]
```

They lazily import their heavy dependencies and raise a clear message if those
are missing — the zero-download demo never touches them.

## Honest caveats

- **This is a demonstration, not a model ranking.** The default "models" are
  transparent lexical heuristics chosen to make the over-refusal *mechanism*
  visible and reproducible on a CPU — not real LLM guardrails. Point the real
  backends at Llama Guard / Prompt Guard to score actual models.
- **The dataset is small and hand-authored** (adapted in spirit from public
  suites, not copied). 240 prompts is enough to demonstrate the effect, not to
  make statistically robust claims. Do not quote the absolute percentages as
  guardrail capabilities.
- **The lexicon is deliberately simple.** It reproduces the *behaviour* real
  lexical guardrails exhibit (topic/intent vocabulary collision) without
  claiming to be state-of-the-art classification.
- **The composite encodes a value judgement** — that a usable guardrail must be
  both safe and non-obstructive. Teams with different risk tolerances should
  read FPR and recall directly rather than trusting a single number.

## Layout

```
overguard/
  lexicon.py     shared signal extractor (harm terms vs benign cues)
  runners.py     guardrail profiles + optional Ollama/HF adapters
  scorer.py      FPR/FNR/precision/recall/F1/composite, ranking, per-category
  reporter.py    Markdown + self-contained HTML leaderboard
  cli.py         run / leaderboard / models / headline
  data/          committed benign.jsonl + harmful.jsonl (240 prompts)
scripts/build_data.py   regenerates the dataset deterministically
results/         committed predictions, metrics, leaderboard.html + .md
tests/           40 pytest cases
```

## License

MIT — see [LICENSE](LICENSE). Built by Dhanush Shankar.
