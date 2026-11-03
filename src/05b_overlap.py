"""Step 6b: how many Cook residents lose BOTH Medicaid and SNAP, so people are never double counted.

Only ACA adults can lose Medicaid here, so overlap = Medicaid losers who also lose SNAP. Using PUMS ACA-like adults
(broad universe, step 4), each person gets a probability of losing each program by Dec of each year (mid etc.):
  Medicaid  subject: 1-(1-work req)(1-verification)(1-renewal); exempt: 1-(1-paperwork)(1-renewal);
            scaled so the PUMS average equals the step 5 county rate (excl. noncitizens)
  SNAP      only if in a SNAP household. Time-limited: min(1, time-limit losses / time-limited pool);
            everyone on SNAP: other beyond-trend losses / Sept 2025 caseload (step 6)
Within each group, the two losses may be unrelated or move together, so overlap is a RANGE:
  low  = independent:        sum w * pM * pS
  high = fully correlated:   sum w * min(pM, pS)
  central = midpoint (shown with the range)
Noncitizens: Medicaid noncitizen losers x share of noncitizen ACA-like adults who live in a SNAP household
(the SNAP noncitizen cut, Apr 2026, hits the same immigration categories).
Shares come from PUMS; counts always from the step 5/6 county totals.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, RAW, load_params  # noqa: E402
from lib.ledger import Ledger, load  # noqa: E402

STEP = "05b_overlap"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
SC = P["meta"]["scenarios"]
YEARS = P["meta"]["analysis_years"]
L = load().set_index("id")
v = lambda i: float(L.loc[i, "value"])  # noqa: E731

f = pd.read_csv(PROC / "pums_flags.csv", dtype={"SERIALNO": str, "SPORDER": str})
cit = pd.read_csv(RAW / f"pums/pums_{P['geography']['pums_year']}_5yr_cook.csv", dtype=str, usecols=["SERIALNO", "SPORDER", "CIT"])
f = f.merge(cit, on=["SERIALNO", "SPORDER"], how="left", validate="1:1")
ck.no_nulls("every PUMS person has CIT", f, ["CIT"])
u = f[f.mcd_universe].copy()
w = u.PWGTP.astype(float)
ck.close("PUMS universe weight matches step 4", w.sum(), v("mcd_pums_universe_weighted"), rel_tol=1e-9)
on_snap = u.snap_on_snap.astype(bool)
led.derived("ovl_share_aca_adults_in_snap_households", (w * on_snap).sum() / w.sum(), "share",
            "weighted share of PUMS ACA-like adults living in a SNAP household (FS=1)", ["mcd_pums_universe_weighted"])
nc = u.CIT == "5"
nc_on_snap = led.derived("ovl_share_noncitizen_aca_adults_in_snap_households",
                         (w * (nc & on_snap)).sum() / (w * nc).sum(), "share",
                         "weighted share of noncitizen (CIT=5) ACA-like adults in a SNAP household", ["mcd_pums_universe_weighted"])

mcd_an = pd.read_csv(OUT / "tables" / "medicaid_annual.csv").set_index(["scenario", "year"])
snp_an = pd.read_csv(OUT / "tables" / "snap_annual.csv").set_index(["scenario", "year"])
base = v("mcd_baseline_aca_adults")
target_office = v("snap_wave1_calibration_target_office")
pool_office = v("snap_time_limited_pool_2026_office")
snap_base = v("snap_cook_persons_county_pdf_2025_09")

rows, pp = [], []
for sc in SC:
    adj = v(f"snap_residence_adj_{sc}")
    r_wr, r_ver = v(f"mcd_loss_rate_subject_{sc}"), v(f"mcd_verification_increase_2028_{sc}")
    r_pw, r_ren = v(f"mcd_loss_rate_exempt_paperwork_{sc}"), v(f"mcd_renewal_6mo_loss_rate_{sc}")
    nc_m, nc_s = v(f"mcd_noncitizen_loss_cook_{sc}"), v(f"snap_noncitizen_loss_cook_{sc}")
    w1, w2 = v(f"snap_hr1_persons_lost_to_2026_09_{sc}"), v(f"snap_second_wave_persons_{sc}")
    tl_w1 = target_office * adj
    other = max(0.0, w1 - tl_w1 - nc_s)
    p_other = other / snap_base
    for y in YEARS:
        M = mcd_an.loc[(sc, y), "off_coverage_dec"]
        S = snp_an.loc[(sc, y), "persons_off_dec"]
        # Medicaid probability by group, scaled to the county rate for this year (excl. noncitizens)
        T = (M - nc_m) / base
        p_m = pd.Series(1 - (1 - r_pw) * (1 - r_ren), index=u.index)
        p_m[u.mcd_subject] = 1 - (1 - r_wr) * (1 - r_ver) * (1 - r_ren)
        p_m = (p_m * T / ((w * p_m).sum() / w.sum())).clip(upper=1) if T > 0 else p_m * 0
        # SNAP probability (zero if not in a SNAP household)
        tl_losses = tl_w1 + (w2 if y >= 2027 else 0)
        p_tl = min(1.0, tl_losses / (pool_office * adj))
        p_s = pd.Series(0.0, index=u.index)
        p_s[on_snap] = p_other
        p_s[on_snap & u.snap_time_limited] = 1 - (1 - p_tl) * (1 - p_other)
        mm = (w * p_m).sum()
        f_lo = (w * p_m * p_s).sum() / mm if mm else 0.0
        f_hi = (w * pd.concat([p_m, p_s], axis=1).min(axis=1)).sum() / mm if mm else 0.0
        both_nc = nc_m * nc_on_snap
        lo, hi = f_lo * (M - nc_m) + both_nc, f_hi * (M - nc_m) + both_nc
        mid = (lo + hi) / 2
        if y == YEARS[-1]:  # per-person chances, for the "who loses both" profile (step 05d)
            pp.append(pd.DataFrame({"SERIALNO": u.SERIALNO, "SPORDER": u.SPORDER, "scenario": sc, "p_medicaid": p_m,
                                    "p_snap": p_s, "p_both_low": p_m * p_s,
                                    "p_both_high": pd.concat([p_m, p_s], axis=1).min(axis=1)}))
        rows.append(dict(scenario=sc, year=y, medicaid_lost=M, snap_lost=S, share_mcd_losers_also_snap_low=f_lo,
                         share_mcd_losers_also_snap_high=f_hi, both_low=lo, both_central=mid, both_high=hi,
                         only_medicaid=M - mid, only_snap=S - mid, unique_residents=M + S - mid,
                         unique_low=M + S - hi, unique_high=M + S - lo, naive_sum=M + S))
        ck.true(f"[{sc} {y}] 0 <= overlap low <= high <= smaller program", 0 <= lo <= hi <= min(M, S) + 1e-6)
        ins = [f"mcd_off_coverage_dec_{y}_{sc}", f"snap_persons_off_dec_{y}_{sc}", "mcd_pums_universe_weighted",
               f"mcd_noncitizen_loss_cook_{sc}", "ovl_share_noncitizen_aca_adults_in_snap_households"]
        for k, val in (("both_low", lo), ("both_central", mid), ("both_high", hi)):
            led.derived(f"ovl_{k}_{y}_{sc}", val, "people",
                        "people off both Medicaid and SNAP, end of Dec (PUMS joint probabilities x county totals)", ins)
        for k, val in (("only_medicaid", M - mid), ("only_snap", S - mid), ("unique_residents", M + S - mid)):
            led.derived(f"ovl_{k}_{y}_{sc}", val, "people", f"from mcd/snap totals minus ovl_both_central_{y}_{sc}",
                        [f"ovl_both_central_{y}_{sc}", f"mcd_off_coverage_dec_{y}_{sc}", f"snap_persons_off_dec_{y}_{sc}"])

res = pd.DataFrame(rows)
pd.concat(pp).to_csv(PROC / f"ovl_person_probs_{YEARS[-1]}.csv", index=False)
for y in YEARS:
    a = res[res.year == y].set_index("scenario")
    ck.ordered(f"{y} unique residents: low <= mid <= high", *(a.loc[s, "unique_residents"] for s in SC))
res.to_csv(OUT / "tables" / "medicaid_snap_overlap.csv", index=False)
pd.set_option("display.width", 220)
show = res[["scenario", "year", "medicaid_lost", "snap_lost", "both_low", "both_central", "both_high", "only_medicaid",
            "only_snap", "unique_residents", "naive_sum"]]
print(show.round(0).to_string(index=False))
print(f"ACA-like adults in SNAP households: {led.rows['ovl_share_aca_adults_in_snap_households']['value']:.1%}; "
      f"noncitizen ACA-like adults in SNAP households: {nc_on_snap:.1%}")
ck.finish()
led.save()
