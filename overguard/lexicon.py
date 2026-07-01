"""Shared lexicon + a tiny, deterministic content classifier.

The heuristic guardrail backends in :mod:`overguard.runners` all lean on the
same signal-extraction routine defined here. Keeping it in one place means the
"models" differ only in their *decision policy* (thresholds / whether they
respect benign framing), not in how they read a prompt -- which is exactly the
axis this benchmark studies.

None of this is meant to be a state-of-the-art classifier. It is a transparent,
offline stand-in that reproduces the *behaviour* real guardrails exhibit:
lexical models over-block benign-but-sensitive prompts because the risky topic
and the benign intent share vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

# Terms that flag a *potentially* dangerous topic. Crucially, benign security
# questions ("how does SQL injection work so I can defend my app?") contain
# these too -- that collision is the entire reason over-refusal happens.
HARM_TERMS: List[str] = [
    "sql injection", "xss", "cross-site scripting", "csrf", "ransomware",
    "malware", "spyware", "keylogger", "rootkit", "trojan", "computer virus",
    "botnet", "ddos", "phishing", "exploit", "buffer overflow",
    "privilege escalation", "backdoor", "bomb", "explosive", "detonator",
    "grenade", "firearm", "handgun", "rifle", "ammunition", "silencer",
    "poison", "cyanide", "ricin", "nerve agent", "methamphetamine", "cocaine",
    "heroin", "fentanyl", "counterfeit", "money laundering", "launder",
    "forge", "hack", "brute force", "crack the password", "steal",
    "credit card number", "identity theft", "untraceable", "evade the police",
    "smuggle", "pick a lock", "lockpick", "hotwire", "poison", "weapon",
    "kill", "attack", "breach", "data breach", "scam",
]

# Cues that a prompt is educational / defensive / clearly legitimate. A
# context-aware guardrail uses these to *forgive* a scary-looking topic.
BENIGN_CUES: List[str] = [
    "protect", "defend", "secure my", "prevent", "mitigate", "safely",
    "legally", "awareness", "educational", "learn", "understand", "history",
    "historical", "essay", "symptom", "first aid", "recover from", "dispose",
    "recycle", "my own", "homework", "research paper", "fictional", "novel",
    "for a movie", "defensive", "harden", "audit", "patch", "best practice",
    "ethically", "with permission", "authorized", "penetration test",
    "pentest", "ctf", "blue team", "how do i stop", "how can i tell if",
]

# Everyday domains where a "scary" word is almost certainly innocent.
BENIGN_DOMAIN: List[str] = [
    "process", "python", "javascript", "linux", "server", "database",
    "cooking", "recipe", "kitchen", "garden", "woodworking", "carving",
    "craft", "kids", "toy", "pet", "houseplant", "camping", "hunting license",
    "sport", "video game", "chess", "boxing", "self-defense class",
]


@dataclass
class Signals:
    """Extracted signals for a single prompt."""

    harm: int          # number of distinct harmful-topic terms present
    benign: int        # number of distinct benign-context cues present
    harm_terms: List[str]
    benign_terms: List[str]


def _count(text: str, terms: List[str]) -> List[str]:
    lowered = text.lower()
    return sorted({t for t in terms if t in lowered})


def analyze(prompt: str) -> Signals:
    """Extract harm/benign signals from a prompt. Pure and deterministic."""
    harm_terms = _count(prompt, HARM_TERMS)
    benign_terms = _count(prompt, BENIGN_CUES + BENIGN_DOMAIN)
    return Signals(
        harm=len(harm_terms),
        benign=len(benign_terms),
        harm_terms=harm_terms,
        benign_terms=benign_terms,
    )
