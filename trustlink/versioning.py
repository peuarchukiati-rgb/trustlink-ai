"""Versioning + reproducibility helpers.

Every scoring run records which engine / feature-spec / weights / bands versions
produced it, plus a hash of the inputs, so any decision can be reproduced exactly.
"""
from __future__ import annotations

import functools
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

ENGINE_VERSION = "0.1.0"

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


@functools.lru_cache(maxsize=None)
def _load_yaml(name: str) -> dict:
    with open(_CONFIG_DIR / name, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_feature_spec() -> dict:
    return _load_yaml("feature_spec.yaml")


def load_weights(mode: str = "hand") -> dict:
    """mode='hand' -> expert weights (default, hits 742); mode='calibrated' -> data-learned (#5)."""
    return _load_yaml("weights_calibrated.yaml" if mode == "calibrated" else "weights.yaml")


def load_bands() -> dict:
    return _load_yaml("bands.yaml")


def config_versions() -> dict[str, str]:
    return {
        "engine": ENGINE_VERSION,
        "feature_spec": str(load_feature_spec().get("spec_version")),
        "weights": str(load_weights().get("weights_version")),
        "bands": str(load_bands().get("bands_version")),
    }


def _canonical(obj: Any) -> Any:
    """Make inputs JSON-serialisable in a stable, order-independent way."""
    from dataclasses import asdict, is_dataclass
    from datetime import date
    from enum import Enum

    if is_dataclass(obj):
        return _canonical(asdict(obj))
    if isinstance(obj, dict):
        return {k: _canonical(obj[k]) for k in sorted(obj, key=str)}
    if isinstance(obj, (list, tuple)):
        return [_canonical(x) for x in obj]
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def input_hash(*parts: Any) -> str:
    payload = json.dumps(_canonical(list(parts)), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def make_snapshot(*, borrower, application, transactions, feature_values, as_of) -> dict:
    """The audit record: input fingerprint + feature values + all versions."""
    return {
        "input_hash": input_hash(borrower, application, transactions),
        "as_of": as_of.isoformat(),
        "feature_values": {k: round(v, 6) for k, v in sorted(feature_values.items())},
        "versions": config_versions(),
    }
