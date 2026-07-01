"""Dataset integrity: 240 committed prompts, clean labels, unique ids."""

from __future__ import annotations

import pytest

from overguard.datasets import dataset_stats, load_dataset


def test_loads_240_prompts():
    prompts = load_dataset()
    assert len(prompts) == 240


def test_balanced_benign_and_harmful():
    stats = dataset_stats(load_dataset())
    assert stats["total"] == 240
    assert stats["benign"] == 120
    assert stats["harmful"] == 120


def test_labels_are_clean():
    for p in load_dataset():
        assert p.label in ("benign", "harmful")
        assert p.prompt.strip(), f"empty prompt for {p.id}"
        assert p.category, f"missing category for {p.id}"


def test_ids_are_unique():
    ids = [p.id for p in load_dataset()]
    assert len(ids) == len(set(ids))


def test_should_block_matches_label():
    for p in load_dataset():
        assert p.should_block == (p.label == "harmful")


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(data_dir=tmp_path)


def test_every_benign_category_present():
    stats = dataset_stats(load_dataset())
    cats = stats["categories"]
    for expected in ("security_education", "tech_homonym", "health_medical"):
        assert cats.get(expected, 0) > 0
