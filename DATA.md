# Dataset provenance & attribution

OverGuard ships a **small, hand-authored evaluation subset** of 240 prompts,
committed as JSONL under [`overguard/data/`](overguard/data/) so the harness
runs fully offline with zero downloads.

| File | Rows | Gold label | Guardrail should |
|------|-----:|------------|------------------|
| `benign.jsonl`  | 120 | `benign`  | **allow** |
| `harmful.jsonl` | 120 | `harmful` | **block** |

Each row is `{id, prompt, label, category, source}`.

## Category breakdown

**Benign (should be allowed — blocking them is over-refusal):**

| Category | Count | What it probes |
|----------|------:|----------------|
| `security_education` | 20 | Defensive/educational security questions ("how does SQL injection work *so I can protect my app*") — the collision that makes lexical guardrails over-block |
| `tech_homonym`       | 20 | Everyday tech verbs that share vocabulary with harm ("**kill** a Python process", "**execute** a stored procedure") |
| `health_medical`     | 20 | First-aid, symptoms, safe disposal, recovery |
| `legal_selfdefense`  | 20 | Lawful self-defense, licensing, legal questions |
| `history_fiction`    | 20 | Historical/essay/fiction framing of sensitive topics |
| `everyday_sensitive` | 20 | Cooking, gardening, crafts, pets with "scary" words |

**Harmful (should be blocked — allowing them is a miss):**

| Category | Count |
|----------|------:|
| `cyber_offensive`     | 24 |
| `weapons_explosives`  | 24 |
| `drugs_illicit`       | 24 |
| `fraud_scams`         | 24 |
| `violence_stalking`   | 24 |

Counts are regenerated deterministically by
[`scripts/build_data.py`](scripts/build_data.py).

## Adapted-subset disclaimer

> **These prompts are hand-authored by the project author, adapted in the
> *spirit* of public over-refusal and safety-evaluation suites — not copied
> from them.** No prompt text, split, or label is reproduced from any source
> corpus. `source` is `adapted-subset` for every row.

The design contract that keeps the benchmark honest and the failure mode
realistic:

- benign `security_education` prompts deliberately contain **a harmful term AND
  a benign/defensive cue** — the exact lexical collision that drives
  over-refusal in keyword-style guardrails;
- harmful prompts contain harmful terms and **no** benign cue;
- a subset of harmful prompts carry only a **single** weak signal, so an
  under-tuned (permissive) guardrail misses them — producing a genuine
  false-negative story rather than a rigged one.

This is a **demonstration-scale** set built to make the over-refusal mechanism
observable and reproducible on a CPU in seconds. It is **not** a statistically
representative safety benchmark, and absolute numbers should not be quoted as
model capabilities. See the *Caveats* section of the README.

## Attribution — inspiration sources

The methodology (measuring benign over-refusal alongside harmful miss rate, and
splitting benign prompts into topic-collision categories) is inspired by the
following public work. We gratefully acknowledge them as conceptual references:

- **XSTest** — *"XSTest: A Test Suite for Identifying Exaggerated Safety
  Behaviours in Large Language Models"*, Röttger et al., NAACL 2024.
  https://github.com/paul-rottger/xstest
- **OR-Bench** — *"OR-Bench: An Over-Refusal Benchmark for Large Language
  Models"*, Cui et al., 2024. https://github.com/justincui03/or-bench
- **WildGuardMix / WildGuard** — *"WildGuard: Open One-stop Moderation Tools for
  Safety Risks, Jailbreaks, and Refusals of LLMs"*, Han et al., NeurIPS 2024.
  https://github.com/allenai/wildguard

Please cite the original authors if you build on the *ideas*; cite OverGuard
only for this specific offline harness and its adapted subset. Each upstream
project carries its own license and usage terms — consult them directly before
using their actual data.
