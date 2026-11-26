"""Role E: Package portable submission ZIP with integrity and selection checks."""
from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from load_forecaster.tetouan import ZONES


def _latest_dir(root: Path, zone: str, profile: str) -> Path | None:
    base = Path(root) / "outputs/tetouan" / zone / profile
    latest = base / "latest.txt"
    if not latest.is_file():
        return None
    d = base / latest.read_text(encoding="utf-8").strip()
    return d if d.is_dir() else None


def create_submission_zip(root: Path) -> Path:
    """Create submission/IT3190_Tetouan.zip and verify archive integrity."""
    root = Path(root)
    report = root / "reports/tetouan"
    z1_full = _latest_dir(root, "zone1", "full")
    if z1_full is None:
        raise FileNotFoundError("Complete Zone 1 full run before packaging")
    if json.loads((report / "zone1/selection.json").read_text(encoding="utf-8")) != json.loads(
        (z1_full / "selection.json").read_text(encoding="utf-8")
    ):
        raise ValueError("Export latest reports before creating the submission ZIP")

    dest = root / "submission/IT3190_Tetouan.zip"
    dest.parent.mkdir(parents=True, exist_ok=True)

    paths: list[Path] = [
        root / name for name in ["readme.txt", "pyproject.toml", "requirements.txt"] if (root / name).is_file()
    ]
    for folder, pattern in [
        ("src", "*"),
        ("app", "*.py"),
        ("docs", "*.md"),
        ("tests", "test_*.py"),
        ("scripts", "*.py"),
        ("data/tetouan/raw", "*"),
        ("reports/tetouan", "*"),
    ]:
        base_dir = root / folder
        if base_dir.is_dir():
            paths.extend(base_dir.rglob(pattern))

    for fname in [
        "observations.parquet",
        "valid_hours.parquet",
        "features.json",
        "audit.json",
        "column_dictionary.json",
        "splits.json",
        "prepare_resources.json",
    ]:
        f = root / "data/tetouan" / fname
        if f.is_file():
            paths.append(f)

    for z in ZONES:
        for prof in ("full", "smoke"):
            run_dir = _latest_dir(root, z, prof)
            if run_dir is not None:
                paths.append(root / "outputs/tetouan" / z / prof / "latest.txt")
                paths.extend(run_dir.rglob("*"))

    stage = dest.with_suffix(".tmp")
    with ZipFile(stage, "w", ZIP_DEFLATED, compresslevel=5) as archive:
        for path in sorted(set(paths)):
            if path.is_file() and "__pycache__" not in path.parts:
                archive.write(path, path.relative_to(root).as_posix())

    with ZipFile(stage) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
    stage.replace(dest)
    return dest
