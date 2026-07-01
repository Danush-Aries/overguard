"""Guardrail model runners.

Two backend families:

* **Heuristic (default, zero-download)** -- deterministic lexical guardrails.
  Three profiles model the behaviour spectrum real guardrails occupy:
    - ``keyword-heuristic`` : blocks on any risky term, ignores framing
      (the classic over-blocker);
    - ``context-aware``     : forgives clearly benign/educational framing
      (well-tuned; best usefulness-preserving safety);
    - ``permissive``        : only blocks on strong signals (misses subtle
      harmful prompts -> high false-negative rate).

* **Real (optional, gated behind a flag)** -- thin adapters for Ollama and
  Hugging Face transformers (Llama Guard, Prompt Guard, Granite Guardian,
  ShieldGemma). They import their heavy deps lazily and raise a clear message
  when unavailable, so the default path never needs a network or a GPU.

Every backend implements ``predict(prompt) -> "block" | "allow"``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List

from .lexicon import analyze

BLOCK = "block"
ALLOW = "allow"


class Guardrail:
    """Base guardrail interface."""

    name: str = "guardrail"
    backend: str = "base"
    description: str = ""

    def predict(self, prompt: str) -> str:  # pragma: no cover - abstract
        raise NotImplementedError

    def predict_batch(self, prompts: List[str]) -> List[str]:
        return [self.predict(p) for p in prompts]


@dataclass
class HeuristicGuardrail(Guardrail):
    """A transparent lexical guardrail parameterised by its decision policy.

    Parameters
    ----------
    name:
        Registry id / display name.
    harm_threshold:
        Minimum number of distinct harmful-topic terms required to block.
    respect_context:
        If True, a prompt with any benign/educational cue is *allowed* even
        when harmful terms are present (this is what tames over-refusal).
    description:
        Human-readable note surfaced in the leaderboard.
    """

    name: str
    harm_threshold: int = 1
    respect_context: bool = False
    description: str = ""
    backend: str = "heuristic"

    def predict(self, prompt: str) -> str:
        sig = analyze(prompt)
        if sig.harm < self.harm_threshold:
            return ALLOW
        if self.respect_context and sig.benign > 0:
            # Risky vocabulary, but a clear benign/defensive frame -> allow.
            return ALLOW
        return BLOCK


# --------------------------------------------------------------------------- #
# Registry of built-in (zero-download) profiles.
# --------------------------------------------------------------------------- #

_PROFILES: Dict[str, Callable[[], Guardrail]] = {
    "keyword-heuristic": lambda: HeuristicGuardrail(
        name="keyword-heuristic",
        harm_threshold=1,
        respect_context=False,
        description="Naive lexical filter: blocks any risky keyword, blind to "
                    "benign framing. Simulates an over-tuned pattern classifier.",
    ),
    "context-aware": lambda: HeuristicGuardrail(
        name="context-aware",
        harm_threshold=1,
        respect_context=True,
        description="Blocks risky topics but forgives clear educational / "
                    "defensive framing. Simulates a well-tuned guardrail "
                    "(Llama-Guard-3 class behaviour).",
    ),
    "permissive": lambda: HeuristicGuardrail(
        name="permissive",
        harm_threshold=2,
        respect_context=True,
        description="Blocks only on strong, multi-signal harm. Simulates an "
                    "under-tuned small model (Prompt-Guard class) that misses "
                    "subtle harmful prompts.",
    ),
}

# Optional real backends. Kept out of the default path; require --backend.
_REAL_BACKENDS = {"ollama", "hf"}


def list_profiles() -> List[str]:
    return list(_PROFILES.keys())


def get_runner(model_id: str, backend: str = "heuristic") -> Guardrail:
    """Return a guardrail instance.

    ``backend='heuristic'`` (default) resolves ``model_id`` against the built-in
    profiles. ``backend='ollama'`` or ``'hf'`` construct optional real adapters
    that lazily import heavy dependencies.
    """
    if backend == "heuristic":
        if model_id not in _PROFILES:
            raise KeyError(
                f"Unknown profile {model_id!r}. "
                f"Available: {', '.join(_PROFILES)}"
            )
        return _PROFILES[model_id]()
    if backend == "ollama":
        return OllamaGuardrail(model_id)
    if backend == "hf":
        return HFGuardrail(model_id)
    raise ValueError(
        f"Unknown backend {backend!r}. "
        f"Use 'heuristic' (default) or one of {sorted(_REAL_BACKENDS)}."
    )


# --------------------------------------------------------------------------- #
# Optional real adapters (lazy imports; never touched on the default path).
# --------------------------------------------------------------------------- #

class OllamaGuardrail(Guardrail):
    """Adapter for guardrail models served locally by Ollama.

    Example models: ``llama-guard3``, ``granite3-guardian``. Requires a running
    Ollama daemon and the ``ollama`` Python package. Offline by design (local
    daemon), but still gated behind ``--backend ollama`` so the default demo
    needs nothing installed.
    """

    backend = "ollama"

    def __init__(self, model_id: str, host: str = "http://localhost:11434"):
        self.name = f"ollama:{model_id}"
        self.model_id = model_id
        self.host = host
        self.description = f"Real guardrail {model_id} served via Ollama."

    def predict(self, prompt: str) -> str:  # pragma: no cover - needs daemon
        try:
            import ollama  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "The 'ollama' package is required for --backend ollama. "
                "Install it and pull a guardrail model, e.g. "
                "`pip install ollama && ollama pull llama-guard3`."
            ) from exc
        client = ollama.Client(host=self.host)
        resp = client.chat(model=self.model_id, messages=[
            {"role": "user", "content": prompt},
        ])
        text = resp["message"]["content"].strip().lower()
        # Llama-Guard-style output: first token 'safe' / 'unsafe'.
        return BLOCK if text.startswith("unsafe") else ALLOW


class HFGuardrail(Guardrail):
    """Adapter for Hugging Face transformers guardrail classifiers.

    Example models: ``meta-llama/Prompt-Guard-86M``,
    ``meta-llama/Llama-Guard-3-1B``, ``ibm-granite/granite-guardian-3.0-2b``,
    ``google/shieldgemma-2b``. Requires ``transformers`` + ``torch`` and a
    (one-time) model download, hence gated behind ``--backend hf``.
    """

    backend = "hf"

    def __init__(self, model_id: str):
        self.name = f"hf:{model_id.split('/')[-1]}"
        self.model_id = model_id
        self.description = f"Real guardrail {model_id} via transformers."
        self._pipe = None

    def _load(self):  # pragma: no cover - needs torch + download
        if self._pipe is None:
            try:
                from transformers import pipeline
            except ImportError as exc:
                raise RuntimeError(
                    "transformers + torch are required for --backend hf. "
                    "Install with `pip install overguard[real]`."
                ) from exc
            self._pipe = pipeline("text-classification", model=self.model_id)
        return self._pipe

    def predict(self, prompt: str) -> str:  # pragma: no cover - needs download
        pipe = self._load()
        out = pipe(prompt)[0]
        label = str(out.get("label", "")).lower()
        # Prompt-Guard: labels include 'jailbreak'/'injection'; ShieldGemma /
        # Llama-Guard: 'unsafe'. Treat any of those as a block.
        blocked = any(k in label for k in ("unsafe", "jailbreak", "injection", "malicious"))
        return BLOCK if blocked else ALLOW
