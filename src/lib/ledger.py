"""Results ledger: every number that feeds an output, with where it came from.

Each entry: id, value, unit, label (observed / derived / assumed), formula, inputs, source, step.
Charts and tables read from output/ledger.csv only, so any plotted number can be traced
back to raw files with:  python src/trace.py <id>

    led = Ledger("04_medicaid")
    base = led.from_params("mcd_baseline", "medicaid.baseline_aca_adults", unit="people")
    led.derived("mcd_loss_2027_mid", base * share * rate, unit="people",
                formula="mcd_baseline * subject_share_a * loss_rate_mid",
                inputs=["mcd_baseline", "subject_share_a", "loss_rate_mid"])
    led.save()
"""
import re

import pandas as pd

from .common import OUT, load_params, param

LEDGER = OUT / "ledger.csv"
COLS = ["id", "value", "unit", "label", "formula", "inputs", "source", "step"]
LABELS = {"observed", "derived", "assumed"}
ID_RE = re.compile(r"^[a-z0-9_.\-]+$")


class Ledger:
    def __init__(self, step):
        self.step = step
        self.rows = {}
        self.params = load_params()

    def _add(self, id, value, unit, label, formula="", inputs=(), source=""):
        if not ID_RE.match(id):
            raise ValueError(f"bad ledger id {id!r}: use lowercase letters, digits, _ . -")
        if label not in LABELS:
            raise ValueError(f"{id}: label must be one of {LABELS}, got {label!r}")
        if label == "derived" and not inputs:
            raise ValueError(f"{id}: derived values must list their inputs")
        if label in ("observed", "assumed") and not source:
            raise ValueError(f"{id}: {label} values need a source")
        self.rows[id] = dict(id=id, value=float(value), unit=unit, label=label, formula=formula,
                             inputs=";".join(inputs), source=source, step=self.step)
        return float(value)

    def observed(self, id, value, unit, source, formula=""):
        return self._add(id, value, unit, "observed", formula, (), source)

    def assumed(self, id, value, unit, source):
        return self._add(id, value, unit, "assumed", "", (), source)

    def derived(self, id, value, unit, formula, inputs, source=""):
        missing = [i for i in inputs if i not in self.rows and i not in _existing_ids()]
        if missing:
            raise KeyError(f"{id}: inputs not in ledger: {missing}")
        return self._add(id, value, unit, "derived", formula, inputs, source)

    def from_params(self, id, path, unit, scenario=None):
        """Record a params.yaml value, keeping its status and source."""
        node = param(path, self.params)
        if scenario:
            node = {**node, **node[scenario]}  # scenario node inherits parent's source/note
        value, status = node["value"], node.get("status", "assumed")
        if value is None:
            raise ValueError(f"params.yaml {path} has no value yet")
        status = status if status in LABELS else "assumed"
        source = node.get("source") or f"params.yaml:{path}" + (f".{scenario}" if scenario else "")
        if status == "derived":
            return self._add(id, value, unit, "assumed", "", (), f"{source} (derived outside pipeline)")
        return self._add(id, value, unit, status, "", (), source)

    def save(self):
        old = load()
        old = old[~old.id.isin(self.rows)]
        old = old[old.step != self.step]
        new = pd.concat([old, pd.DataFrame(self.rows.values(), columns=COLS)], ignore_index=True)
        new.to_csv(LEDGER, index=False)
        print(f"ledger: {len(self.rows)} entries from {self.step} ({len(new)} total)")


def load():
    if LEDGER.exists():
        return pd.read_csv(LEDGER, dtype={"inputs": str, "formula": str, "source": str}).fillna("")
    return pd.DataFrame(columns=COLS)


def _existing_ids():
    return set(load().id)
