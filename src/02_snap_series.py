"""Step 3: Cook SNAP monthly series, observed drop, and drop beyond the pre-H.R. 1 trend.

Baseline month: Sept 2025 (first month after the July 2025 IDHS reporting break, and the plan's anchor).
Counterfactual = what Cook SNAP persons would have been on the pre-H.R. 1 trend, continued from Sept 2025.
Pre-period trend: log-linear fit, Jan 2024-Jun 2025 (18 months).
  high: flat counterfactual; every person lost since Sept 2025 is attributed.
  mid:  drop beyond the pre-period trend from Dec 2025, when IDHS first applied the H.R. 1 work requirement
        (countable months recorded, later removed after a court ruling; IDHS IM 01/15/2026, CN 26.01).
  low:  drop beyond the pre-period trend from Feb 2026, the legal start of the time limit.
Start months come from params.yaml (snap.attribution_start).
Pre-period ends June 2025 (before the July 2025 break and before H.R. 1 was signed, July 4 2025).
The "beyond trend" drop also includes non-H.R. 1 shocks (e.g. the Nov 2025 shutdown); see methods.md.

Office-based numbers are scaled to Cook residents by the Sept 2025 county/office ratio (params: snap.residence_adjustment).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, load_params  # noqa: E402
from lib.ledger import Ledger  # noqa: E402
from lib.tracer import flush, trace, tracers  # noqa: E402

STEP = "02_snap_series"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
IDHS = "IDHS SNAP Data by Servicing Office"

s = pd.read_csv(PROC / "snap_cook_monthly.csv")
s["period"] = pd.PeriodIndex(s.month, freq="M")
s = s.set_index("period").sort_index()

# ---- observed monthly values into the ledger ---------------------------------------------------
for p, r in s.iterrows():
    tag = p.strftime("%Y_%m")
    led.observed(f"snap_cook_persons_{tag}", r.persons, "people", f"{IDHS}, {r.source_ref}")
    led.observed(f"snap_cook_households_{tag}", r.households, "households", f"{IDHS}, {r.source_ref}")

BASE, LATEST = pd.Period("2025-09", "M"), s.index.max()
b, l = BASE.strftime("%Y_%m"), LATEST.strftime("%Y_%m")
ck.equal("latest IDHS month is Sept 2026 (update if newer data is fetched)", str(LATEST), "2026-09", soft=True)

# ---- residence adjustment (county PDF by residence / office table, Sept 2025) ----------------------
cty = pd.read_csv(PROC / "snap_county_2025_09.csv").set_index("county").persons
led.observed("snap_cook_persons_county_pdf_2025_09", cty["Cook"], "people",
             "IDHS SNAP Individual Counts by Counties, Sept 2025, page 1")
ratio = led.derived("snap_residence_ratio", cty["Cook"] / s.loc[BASE, "persons"], "ratio",
                    "snap_cook_persons_county_pdf_2025_09 / snap_cook_persons_2025_09",
                    ["snap_cook_persons_county_pdf_2025_09", f"snap_cook_persons_{b}"])
ck.between("residence ratio plausible (1.00-1.10)", ratio, 1.0, 1.10)
adj = {}
for sc in ("low", "mid", "high"):
    node = P["snap"]["residence_adjustment"][sc]
    if node["value"] == "from_sept2025_county_office_ratio":
        adj[sc] = led.derived(f"snap_residence_adj_{sc}", ratio, "ratio", "snap_residence_ratio", ["snap_residence_ratio"])
    else:
        adj[sc] = led.from_params(f"snap_residence_adj_{sc}", "snap.residence_adjustment", "ratio", scenario=sc)

# ---- observed drop -----------------------------------------------------------------------------
for unit, col in (("people", "persons"), ("households", "households")):
    drop = led.derived(f"snap_observed_drop_{col}", s.loc[BASE, col] - s.loc[LATEST, col], unit,
                       f"snap_cook_{col}_{b} - snap_cook_{col}_{l}",
                       [f"snap_cook_{col}_{b}", f"snap_cook_{col}_{l}"])
    ck.true(f"observed {col} drop is positive", drop > 0)

# ---- pre-period trends (log-linear: monthly % change) ----------------------------------------------
pre = s.loc[: pd.Period("2025-06", "M")]
ck.equal("pre-period has no reporting break (no SPECIALTY row before Jul 2025)", int(pre.series_break.sum()), 0)


def monthly_rate(df):
    t = np.array([(p - df.index[0]).n for p in df.index], dtype=float)  # gaps (Feb 2024) handled by real time
    return float(np.exp(np.polyfit(t, np.log(df.persons.values), 1)[0]) - 1)


rate = monthly_rate(pre)
led.derived("snap_trend_rate", rate, "monthly % change", "log-linear fit of Cook persons, Jan 2024-Jun 2025",
            [f"snap_cook_persons_{p.strftime('%Y_%m')}" for p in pre.index])
ck.between("pre-period trend is a mild decline (-1%..+0.5% per month)", rate, -0.01, 0.005)
alt = monthly_rate(pre.loc[pd.Period("2025-01", "M"):])
ck.close("pre-period trend is stable (Jan-Jun 2025 fit within 0.1 pt of 18-month fit)", alt, rate, abs_tol=0.001,
         soft=True, detail=f"Jan-Jun 2025 fit {alt:.4%}/month")

START = {sc: pd.Period(P["snap"]["attribution_start"][sc]["value"], "M") for sc in ("low", "mid")}
for sc, per in START.items():
    led.observed(f"snap_attribution_start_{sc}", per.year + per.month / 100, "year.month",
                 P["snap"]["attribution_start"][sc]["source"])

# ---- counterfactual series and drop beyond trend ------------------------------------------------------
months_after = [p for p in s.index if p >= BASE]
cf = pd.DataFrame([dict(month=str(p), observed=s.loc[p, "persons"],
                        counterfactual_trend=s.loc[BASE, "persons"] * (1 + rate) ** (p - BASE).n,
                        counterfactual_flat=s.loc[BASE, "persons"]) for p in months_after])
cf["observed_change"] = cf.observed.diff()
cf["trend_change"] = cf.counterfactual_trend.diff()
cf["excess_change"] = cf.observed_change - cf.trend_change
n = (LATEST - BASE).n
last = cf.iloc[-1]
cf_trend = led.derived(f"snap_counterfactual_persons_{l}", last.counterfactual_trend, "people",
                       f"snap_cook_persons_{b} * (1 + snap_trend_rate)^{n}", [f"snap_cook_persons_{b}", "snap_trend_rate"])
ck.close("monthly excess changes sum to (counterfactual - observed) at latest month",
         -cf.excess_change.sum(), cf_trend - s.loc[LATEST, "persons"], abs_tol=1)
office = {"high": led.derived("snap_beyond_trend_office_high", s.loc[BASE, "persons"] - s.loc[LATEST, "persons"], "people",
                              f"snap_cook_persons_{b} - snap_cook_persons_{l} (flat counterfactual)",
                              [f"snap_cook_persons_{b}", f"snap_cook_persons_{l}"])}
for sc, per in START.items():
    office[sc] = led.derived(f"snap_beyond_trend_office_{sc}", -cf[cf.month >= str(per)].excess_change.sum(), "people",
                             f"sum over {per}..{LATEST} of (trend change - observed change)",
                             [f"snap_cook_persons_{p.strftime('%Y_%m')}" for p in s.index if p >= per - 1]
                             + ["snap_trend_rate", f"snap_attribution_start_{sc}"])
for sc in ("low", "mid", "high"):
    led.derived(f"snap_hr1_persons_lost_to_{l}_{sc}", office[sc] * adj[sc], "people",
                f"snap_beyond_trend_office_{sc} * snap_residence_adj_{sc}",
                [f"snap_beyond_trend_office_{sc}", f"snap_residence_adj_{sc}"])

v = {sc: led.rows[f"snap_hr1_persons_lost_to_{l}_{sc}"]["value"] for sc in ("low", "mid", "high")}
ck.ordered("H.R. 1 SNAP persons lost: low <= mid <= high", v["low"], v["mid"], v["high"])
ck.close("high scenario = observed drop x residence adj", v["high"],
         led.rows["snap_observed_drop_persons"]["value"] * adj["high"], abs_tol=1)

# ---- monthly excess changes (for timing: which month carries the cutoffs) --------------------------------
m = cf.copy()
events = {"2025-11": "federal shutdown benefit disruption", "2026-02": "ABAWD time-limit clock starts (Feb 1)",
          "2026-04": "noncitizen SNAP cut (Apr 1)", "2026-05": "first time-limit cutoffs (May 1)"}
m["event"] = m.month.map(events).fillna("")

# Calibration target for the 2027 second wave: excess drop from the first cutoff month through latest
cut = m[m.month >= "2026-05"]
led.derived("snap_excess_drop_may_to_latest_office_mid", -cut.excess_change.sum(), "people",
            f"sum of (trend change - observed change), May 2026 - {LATEST}, mid trend",
            [f"snap_cook_persons_{p.strftime('%Y_%m')}" for p in s.index if p >= pd.Period("2026-04", "M")]
            + ["snap_trend_rate"])
apr_may = m[m.month == "2026-05"].iloc[0]
led.derived("snap_excess_drop_may_2026_office_mid", -apr_may.excess_change, "people",
            "(snap_cook_persons_2026_04 - snap_cook_persons_2026_05) less trend change",
            ["snap_cook_persons_2026_04", "snap_cook_persons_2026_05", "snap_trend_rate"])
ck.true("May 2026 is the largest monthly excess drop (first cutoffs)",
        m.loc[m.excess_change.idxmin(), "month"] == "2026-05", soft=True)

# ---- save --------------------------------------------------------------------------------------------
out = s.reset_index(drop=True)[["month", "households", "persons", "state_persons", "cook_share_persons", "series_break", "note"]]
out.to_csv(OUT / "tables" / "snap_cook_monthly.csv", index=False)
cf.to_csv(OUT / "tables" / "snap_counterfactual.csv", index=False)
m[["month", "observed", "counterfactual_trend", "observed_change", "trend_change", "excess_change", "event"]].to_csv(
    OUT / "tables" / "snap_monthly_excess_mid.csv", index=False)

tm = tracers()["month"]
mm = m[m.month == tm].iloc[0]
trace(STEP, f"month:{tm}", "observed change vs prior month", int(mm.observed_change), "IDHS office table")
trace(STEP, f"month:{tm}", "excess change beyond mid trend", round(float(mm.excess_change)), "observed - trend change")
flush(STEP)

print(m[["month", "observed", "counterfactual_trend", "excess_change", "event"]].round(0).to_string(index=False))
print(f"pre-period trend {rate:.3%}/month")
print({k: round(x) for k, x in v.items()}, "H.R. 1 persons lost (residence basis)")
ck.finish()
led.save()
