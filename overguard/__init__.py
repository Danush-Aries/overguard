"""OverGuard: an offline, CPU-first leaderboard for guardrail over-refusal.

Ranks small guardrail models on how often they FALSELY block benign prompts
(false positives / over-refusal) alongside their miss rate (false negatives),
on committed public-style datasets. No API keys, no downloads on the default
path.
"""

from .datasets import Prompt, dataset_stats, load_dataset
from .reporter import render_html, render_markdown
from .runners import get_runner, list_profiles
from .scorer import Metrics, Prediction, category_fpr, compute_metrics, rank

__version__ = "0.1.0"
__author__ = "Dhanush Shankar"

__all__ = [
    "Prompt", "load_dataset", "dataset_stats",
    "get_runner", "list_profiles",
    "Metrics", "Prediction", "compute_metrics", "category_fpr", "rank",
    "render_html", "render_markdown",
    "__version__", "__author__",
]
