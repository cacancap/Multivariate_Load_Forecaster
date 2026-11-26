"""Role D: Chronological 80/20 split and 3 expanding CV folds with strict 24h+ label embargo."""
from __future__ import annotations

import pandas as pd

from load_forecaster.evaluation import temporal_folds

HOUR = pd.Timedelta(hours=1)


def _bounds(train: pd.DatetimeIndex, evaluation: pd.DatetimeIndex) -> dict[str, str]:
    return {
        "train_start": train[0].isoformat(),
        "train_end": train[-1].isoformat(),
        "eval_start": evaluation[0].isoformat(),
        "eval_end": evaluation[-1].isoformat(),
    }


def _check_bounds(b: dict[str, str]) -> None:
    first, last, start, end = (
        pd.Timestamp(b[k]) for k in ("train_start", "train_end", "eval_start", "eval_end")
    )
    if not first <= last or last + 24 * HOUR >= start or start > end:
        raise ValueError("Train labels must strictly precede evaluation origins (24h+ embargo violated)")


def make_splits(samples_or_origins) -> dict:
    """Create 80/20 train-test split and 3 expanding 28-day CV folds on the full hourly grid."""
    if isinstance(samples_or_origins, pd.DataFrame):
        origins = pd.DatetimeIndex(
            samples_or_origins["origin_time"].drop_duplicates().sort_values()
        )
    else:
        origins = pd.DatetimeIndex(samples_or_origins).drop_duplicates().sort_values()

    complete = pd.date_range(origins.min(), origins.max(), freq="h")
    if not origins.equals(complete) or (origins != origins.floor("h")).any():
        raise ValueError("Supply the complete regular hourly origin grid before filtering samples")

    cut = len(origins) * 4 // 5
    dev = origins[:cut]
    folds = [
        _bounds(tr, va)
        for tr, va in temporal_folds(dev, n_splits=3, test_size=28 * 24, gap=24, max_horizon=24)
    ]
    # origins[:cut - 24] ends at index (cut - 25), leaving 25 hours to origins[cut] (> 24h).
    test = _bounds(origins[: cut - 24], origins[cut:])
    for b in [*folds, test]:
        _check_bounds(b)
    return {"folds": folds, "test": test}
