"""Shared paths and params loading."""
import os
import sys
from pathlib import Path

import yaml

# GDAL data path is normally set by `conda activate`; set it when python.exe is called directly.
_gdal = Path(sys.prefix) / "Library" / "share" / "gdal"
if _gdal.exists():
    os.environ.setdefault("GDAL_DATA", str(_gdal))

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "output"
CHECKS = OUT / "checks"
TRACE = OUT / "trace"
for d in (PROC, OUT, CHECKS, TRACE, OUT / "figures", OUT / "tables"):
    d.mkdir(parents=True, exist_ok=True)


def load_params():
    return yaml.safe_load((ROOT / "params.yaml").read_text(encoding="utf-8"))


def param(path, params=None):
    """Get a params.yaml node by dotted path, e.g. 'medicaid.baseline_aca_adults'."""
    node = params or load_params()
    for key in path.split("."):
        node = node[key]
    return node
