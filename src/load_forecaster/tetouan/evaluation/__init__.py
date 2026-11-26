"""Role D: Chronological splits, baselines, scoring, and peak/ramp critical-hour evaluation."""

from .metrics import compute_metrics, score_run
from .splits import make_splits

__all__ = ["compute_metrics", "make_splits", "score_run"]
