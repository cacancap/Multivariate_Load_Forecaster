"""Role C: Reload saved horizon estimators and enforce causal origin boundaries."""
from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from .train import GRID


def predict_saved(
    out: Path,
    rows: pd.DataFrame,
    model: str = "ridge",
    zone: str | None = None,
) -> np.ndarray:
    """Return raw-unit predictions ordered identically to input rows."""
    if model not in {*GRID, "ridge_no_weather"}:
        raise ValueError(f"Unknown model {model!r}")
    rows = rows.reset_index(drop=True)
    if not (rows["target_time"] == rows["origin_time"] + pd.to_timedelta(rows["horizon"], unit="h")).all():
        raise ValueError("Incorrect horizon or missing origin_time/target_time")

    result = np.empty(len(rows), dtype=float)
    with threadpool_limits(limits=1):
        for h, group in rows.groupby("horizon"):
            h_int = int(h)
            if h_int not in range(1, 25):
                raise ValueError("Horizon outside 1..24")
            state = joblib.load(Path(out) / "models" / f"{model}-h{h_int}.joblib")
            if state["horizon"] != h_int or state["model"] != model:
                raise ValueError("Saved model does not match requested model or horizon")
            if zone is not None and state.get("zone") is not None and state["zone"] != zone:
                raise ValueError(f"Saved model belongs to {state['zone']!r}, requested {zone!r}")
            if group["origin_time"].le(state["latest_train_target"]).any():
                raise ValueError("Requested forecast precedes availability of training labels")
            x = group[state["columns"]].to_numpy(dtype=float)
            if not np.isfinite(x).all():
                raise ValueError("Insufficient feature history (non-finite inputs)")
            result[group.index] = state["estimator"].predict(x)
    return result
