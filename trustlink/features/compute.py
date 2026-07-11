"""Build a FeatureVector by walking the declarative feature spec."""
from __future__ import annotations

from datetime import date

from ..domain.models import Application, Borrower, FeatureVector, Transaction
from ..versioning import load_feature_spec
from .functions import REGISTRY, FeatureContext


def compute_features(
    borrower: Borrower,
    application: Application,
    events: list[Transaction] | tuple[Transaction, ...],
    as_of: date,
) -> FeatureVector:
    spec = load_feature_spec()
    window = int(spec.get("window_months", 6))
    ctx = FeatureContext(
        borrower=borrower,
        application=application,
        events=tuple(events),
        as_of=as_of,
        window_months=window,
    )

    values: dict[str, float] = {}
    coverage: dict[str, float] = {}
    for name, entry in spec["features"].items():
        fn = REGISTRY.get(name)
        if fn is None:
            raise KeyError(f"feature_spec references unknown feature '{name}'")
        value, cov = fn(ctx, int(entry.get("ideal_months", 0)))
        values[name] = value
        coverage[name] = cov

    return FeatureVector(
        values=values,
        coverage=coverage,
        as_of=as_of,
        window_months=window,
        feature_spec_version=str(spec.get("spec_version")),
    )
