"""Unified CLI entrypoint for the 5-role Tetouan 24-hour load forecasting project."""
import os
import sys
from pathlib import Path

for _env_var in (
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "OMP_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "BLIS_NUM_THREADS",
):
    os.environ[_env_var] = "1"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from load_forecaster.tetouan.integration.pipeline import main


if __name__ == "__main__":
    main(root=ROOT)
