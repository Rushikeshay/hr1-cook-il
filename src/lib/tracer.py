"""Tracer units: a few fixed units (zips, a month, an office, a PUMS household) whose values are
logged at every step to output/trace/trace_log.csv, so one row can be followed end to end.

    from lib.tracer import trace, tracers
    for z in tracers()["zips"]:
        trace("06_zip_alloc", f"zip:{z}", "mcd_loss_mid_2027", value, note="county loss x zip share")
"""
from datetime import datetime

import pandas as pd

from .common import TRACE, load_params

LOG = TRACE / "trace_log.csv"
COLS = ["unit", "step", "stage", "value", "note", "run_at"]
_buffer = []


def tracers():
    return load_params()["verification"]["tracers"]


def trace(step, unit, stage, value, note=""):
    _buffer.append(dict(unit=unit, step=step, stage=stage, value=value, note=note,
                        run_at=datetime.now().isoformat(timespec="seconds")))


def flush(step):
    """Replace this step's trace rows and rewrite the per-unit markdown report."""
    global _buffer
    old = pd.read_csv(LOG, dtype=str) if LOG.exists() else pd.DataFrame(columns=COLS)
    new = pd.concat([old[old.step != step], pd.DataFrame(_buffer, columns=COLS)], ignore_index=True)
    new.to_csv(LOG, index=False)
    _buffer = []
    lines = ["# Tracer report", "", "Each tracer unit's value at every pipeline stage.", ""]
    for unit, g in new.groupby("unit", sort=False):
        lines += [f"## {unit}", "", "| step | stage | value | note |", "|---|---|---|---|"]
        lines += [f"| {r.step} | {r.stage} | {r.value} | {r.note} |" for r in g.sort_values("step").itertuples()]
        lines.append("")
    (TRACE / "trace_report.md").write_text("\n".join(lines), encoding="utf-8")
