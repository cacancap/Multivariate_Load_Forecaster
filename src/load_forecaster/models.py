"""Independent estimators per horizon; train-only input and target transforms."""
import numpy as np
from sklearn.compose import TransformedTargetRegressor
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR


DEFAULTS = {
    "ridge": {"alpha": 100.0},
    "random_forest": {"n_estimators": 64, "max_depth": 12, "min_samples_leaf": 4},
    "svr": {"C": 10.0, "epsilon": 0.05, "gamma": "scale", "cache_size": 128},
    "hist_gradient_boosting": {"max_iter": 150, "learning_rate": 0.08, "max_leaf_nodes": 31, "l2_regularization": 1.0, "early_stopping": False},
}


def base_name(name):
    return name.removesuffix("_365")


def build_model(name, params=None, seed=42, threads=4):
    base = base_name(name)
    settings = {**DEFAULTS[base], **(params or {})}
    if base == "ridge":
        return make_pipeline(StandardScaler(), Ridge(**settings))
    if base == "svr":
        return TransformedTargetRegressor(regressor=make_pipeline(StandardScaler(), SVR(**settings)), transformer=StandardScaler())
    if base == "random_forest":
        return RandomForestRegressor(**settings, random_state=seed, n_jobs=min(4, threads))
    return HistGradientBoostingRegressor(**settings, random_state=seed)


def candidates(name, maximum=4, seed=42):
    base = base_name(name)
    rng = np.random.default_rng(seed)
    default = dict(DEFAULTS[base])
    pool = []
    if base == "ridge":
        pool = [{"alpha": float(a)} for a in (0.1, 1, 10, 1000, 10000, 100000)]
    elif base == "random_forest":
        pool = [{**default, "max_depth": d, "min_samples_leaf": leaf} for d in (8, 12, 20, None) for leaf in (2, 8, 16)]
    elif base == "svr":
        pool = [{**default, "C": c, "epsilon": e, "gamma": g} for c in (1, 10, 100) for e in (0.01, 0.1) for g in ("scale", 0.01)]
    else:
        pool = [{**default, "learning_rate": lr, "max_leaf_nodes": leaves, "l2_regularization": reg} for lr in (0.03, 0.1) for leaves in (15, 31) for reg in (0, 10)]
    rng.shuffle(pool)
    unique = [default]
    for item in pool:
        if item not in unique:
            unique.append(item)
    return unique[:min(12, max(1, maximum))]
