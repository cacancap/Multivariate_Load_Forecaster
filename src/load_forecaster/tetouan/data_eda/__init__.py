"""Role A: Data acquisition, cleaning, audit, and exploratory data analysis."""

from .eda import run_eda
from .observations import (
    EXPECTED_ZIP_SHA256,
    MEMBER,
    SOURCE_COLUMNS,
    URL,
    prepare_observations,
    table_from_zip,
)

__all__ = [
    "EXPECTED_ZIP_SHA256",
    "MEMBER",
    "SOURCE_COLUMNS",
    "URL",
    "prepare_observations",
    "run_eda",
    "table_from_zip",
]
