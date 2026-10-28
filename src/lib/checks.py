"""Verification checks. Every check is logged to output/checks/results.csv.

A failed hard check raises CheckFailed, which stops the pipeline (run_all.py).
A failed soft check is logged as WARN and the step continues.

    ck = Checks("01a_snap_offices")
    ck.equal("cook persons June 2026 = published", actual, 686905)
    ck.close(1.0012, 1.0, rel_tol=0.01, name="PUMS pop vs ACS")
    ck.true("no missing months", cond, detail="...")
    ck.finish()   # writes results + report
"""
import math
from datetime import datetime

import pandas as pd

from .common import CHECKS

RESULTS = CHECKS / "results.csv"
COLS = ["step", "check", "status", "expected", "actual", "detail", "run_at"]


class CheckFailed(AssertionError):
    pass


class Checks:
    def __init__(self, step):
        self.step = step
        self.rows = []
        self.failed = []

    # -- core ---------------------------------------------------------------
    def _log(self, name, ok, expected="", actual="", detail="", soft=False):
        status = "PASS" if ok else ("WARN" if soft else "FAIL")
        self.rows.append(dict(step=self.step, check=name, status=status, expected=_fmt(expected),
                              actual=_fmt(actual), detail=detail,
                              run_at=datetime.now().isoformat(timespec="seconds")))
        print(f"  [{status}] {name}" + (f" | expected {_fmt(expected)}, got {_fmt(actual)}" if not ok else ""))
        if not ok and not soft:
            self.failed.append(name)
        return ok

    def true(self, name, cond, detail="", soft=False):
        return self._log(name, bool(cond), "True", bool(cond), detail, soft)

    def equal(self, name, actual, expected, detail="", soft=False):
        return self._log(name, actual == expected, expected, actual, detail, soft)

    def close(self, name, actual, expected, rel_tol=0.0, abs_tol=0.0, detail="", soft=False):
        ok = actual is not None and math.isclose(actual, expected, rel_tol=rel_tol, abs_tol=abs_tol)
        tol = f"rel_tol={rel_tol}" if rel_tol else f"abs_tol={abs_tol}"
        return self._log(name, ok, f"{_fmt(expected)} ({tol})", actual, detail, soft)

    def between(self, name, actual, lo, hi, detail="", soft=False):
        return self._log(name, lo <= actual <= hi, f"[{_fmt(lo)}, {_fmt(hi)}]", actual, detail, soft)

    # -- table helpers --------------------------------------------------------
    def no_nulls(self, name, df, cols=None, soft=False):
        cols = cols or list(df.columns)
        n = int(df[cols].isna().sum().sum())
        return self._log(name, n == 0, 0, n, f"nulls in {cols}", soft)

    def unique(self, name, df, cols, soft=False):
        n = int(df.duplicated(cols).sum())
        return self._log(name, n == 0, 0, n, f"duplicate keys on {cols}", soft)

    def non_negative(self, name, s, soft=False):
        n = int((s < 0).sum())
        return self._log(name, n == 0, 0, n, "negative values", soft)

    def months_contiguous(self, name, months, soft=False):
        m = pd.PeriodIndex(sorted(set(months)), freq="M")
        full = pd.period_range(m.min(), m.max(), freq="M")
        missing = sorted(set(full) - set(m))
        return self._log(name, not missing, "no gaps", f"missing {missing}" if missing else "no gaps", soft=soft)

    def sums_to(self, name, parts_total, whole, abs_tol=0.5, soft=False):
        return self.close(name, float(parts_total), float(whole), abs_tol=abs_tol, soft=soft)

    def ordered(self, name, low, mid, high, soft=False):
        return self._log(name, low <= mid <= high, "low <= mid <= high", f"{_fmt(low)}, {_fmt(mid)}, {_fmt(high)}", soft=soft)

    # -- finish ---------------------------------------------------------------
    def finish(self):
        """Replace this step's rows in results.csv, rebuild report.md, raise if any hard check failed."""
        old = pd.read_csv(RESULTS, dtype=str) if RESULTS.exists() else pd.DataFrame(columns=COLS)
        new = pd.concat([old[old.step != self.step], pd.DataFrame(self.rows, columns=COLS)])
        new.sort_values(["step"], kind="stable").to_csv(RESULTS, index=False)
        write_report(new)
        n_pass = sum(r["status"] == "PASS" for r in self.rows)
        n_warn = sum(r["status"] == "WARN" for r in self.rows)
        print(f"{self.step}: {n_pass} pass, {n_warn} warn, {len(self.failed)} fail")
        if self.failed:
            raise CheckFailed(f"{self.step}: failed checks: {self.failed}")


def write_report(df):
    df = df.fillna("")
    lines = ["# Check report", "", f"Generated {datetime.now():%Y-%m-%d %H:%M}", ""]
    summary = df.groupby(["step", "status"]).size().unstack(fill_value=0)
    lines += ["| step | " + " | ".join(summary.columns) + " |", "|---" * (len(summary.columns) + 1) + "|"]
    lines += [f"| {s} | " + " | ".join(str(v) for v in row) + " |" for s, row in summary.iterrows()]
    bad = df[df.status != "PASS"]
    if len(bad):
        lines += ["", "## Not passing", ""]
        lines += [f"- **{r.status}** `{r.step}` {r.check}: expected {r.expected}, got {r.actual}. {r.detail}"
                  for r in bad.itertuples()]
    (CHECKS / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _fmt(x):
    if isinstance(x, float):
        return f"{x:,.4f}" if abs(x) < 10 else f"{x:,.1f}"
    if isinstance(x, int) and not isinstance(x, bool):
        return f"{x:,}"
    return str(x)
