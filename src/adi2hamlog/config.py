"""Configuration: bundled defaults, optionally overridden by a user JSON file."""

from __future__ import annotations

import copy
import json
from importlib import resources


def _merge(base: dict, over: dict) -> dict:
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _merge(base[k], v)
        else:
            base[k] = v
    return base


def load_config(path=None) -> dict:
    """Load default_config.json; a user file is deep-merged over it (dicts merge, others replace)."""
    text = resources.files("adi2hamlog").joinpath("data/default_config.json").read_text(encoding="utf-8")
    cfg = json.loads(text)
    if path:
        with open(path, encoding="utf-8") as f:
            cfg = _merge(copy.deepcopy(cfg), json.load(f))
    return cfg
