"""Dataset loading for the vendored over-refusal evaluation subset.

Everything here reads committed JSONL from ``overguard/data`` -- no network,
no downloads. See DATA.md for provenance and attribution.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

DATA_DIR = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class Prompt:
    """A single evaluation item."""

    id: str
    prompt: str
    label: str       # "benign" (should allow) or "harmful" (should block)
    category: str
    source: str

    @property
    def should_block(self) -> bool:
        return self.label == "harmful"


def _load_file(path: Path) -> List[Prompt]:
    if not path.exists():
        raise FileNotFoundError(
            f"Dataset file missing: {path}. Run `python scripts/build_data.py`."
        )
    items: List[Prompt] = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            missing = {"id", "prompt", "label", "category"} - row.keys()
            if missing:
                raise ValueError(f"{path}:{lineno} missing fields {missing}")
            if row["label"] not in ("benign", "harmful"):
                raise ValueError(f"{path}:{lineno} bad label {row['label']!r}")
            items.append(Prompt(
                id=row["id"],
                prompt=row["prompt"],
                label=row["label"],
                category=row["category"],
                source=row.get("source", "adapted-subset"),
            ))
    return items


def load_dataset(data_dir: Path | None = None) -> List[Prompt]:
    """Load and return the full benign + harmful evaluation set."""
    base = data_dir or DATA_DIR
    prompts = _load_file(base / "benign.jsonl") + _load_file(base / "harmful.jsonl")
    ids = [p.id for p in prompts]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate prompt IDs detected in dataset.")
    return prompts


def dataset_stats(prompts: List[Prompt]) -> Dict[str, object]:
    """Summary counts, useful for the CLI header and README honesty section."""
    benign = [p for p in prompts if p.label == "benign"]
    harmful = [p for p in prompts if p.label == "harmful"]
    by_cat: Dict[str, int] = {}
    for p in prompts:
        by_cat[p.category] = by_cat.get(p.category, 0) + 1
    return {
        "total": len(prompts),
        "benign": len(benign),
        "harmful": len(harmful),
        "categories": by_cat,
    }
