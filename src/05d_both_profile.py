"""Step 6d: who is likely to lose BOTH Medicaid and SNAP. Profile of Cook ACA-like adults (ACS PUMS 2020-24), each
person weighted by survey weight x their chance of losing both programs by Dec of the last analysis year (step 6b).

Chance of losing both: low end = independent (pM x pS), high end = fully correlated (min(pM, pS)); central = midpoint,
the same rule step 6b uses for the county count. The profile uses the central chance; the profile under the two ends
is kept as a check (if the two ends disagree a lot, the shares are fragile).
Excludes the noncitizen cut (step 6b adds those people separately: about 1-2k residents).
Standard errors: 80 replicate weights x the same chances (chances held fixed). Describes likely losers from a survey
taken before H.R. 1, not people observed losing coverage.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, RAW, load_params  # noqa: E402
from lib.ledger import Ledger, load  # noqa: E402

STEP = "05d_both_profile"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
Y = P["meta"]["analysis_years"][-1]
L = load().set_index("id")
REP = [f"PWGTP{i}" for i in range(1, 81)]
KEY = ["SERIALNO", "SPORDER"]

pr = pd.read_csv(PROC / f"ovl_person_probs_{Y}.csv", dtype={"SERIALNO": str, "SPORDER": str})
ch = pd.read_csv(PROC / "pums_profile_chars.csv", dtype=str)
wt = pd.read_csv(RAW / f"pums/pums_{P['geography']['pums_year']}_5yr_cook.csv", dtype=str, usecols=KEY + ["PWGTP"] + REP)
ck.true("characteristics file has one row per person", not ch.duplicated(KEY).any())

rows = []
for sc, g in pr.groupby("scenario", sort=False):
    d = g.merge(ch, on=KEY, how="left", validate="1:1").merge(wt, on=KEY, how="left", validate="1:1")
    ck.no_nulls(f"[{sc}] every person has weights and characteristics", d, ["PWGTP", "region", "age"])
    W = d[["PWGTP"] + REP].astype(float).to_numpy()
    p = {"central": (d.p_both_low + d.p_both_high) / 2, "low": d.p_both_low, "high": d.p_both_high}
    # check: weighted chance x PUMS matches step 6b's share of Medicaid losers who also lose SNAP
    lo_share = (W[:, 0] * d.p_both_low).sum() / (W[:, 0] * d.p_medicaid).sum()
    ck.close(f"[{sc}] independent-overlap share matches step 6b", lo_share,
             float(pd.read_csv(OUT / "tables" / "medicaid_snap_overlap.csv").query("scenario == @sc and year == @Y")
                   .share_mcd_losers_also_snap_low.iloc[0]), rel_tol=1e-6)
    for c in ("age", "sex", "race_ethnicity", "education", "work_past_12_months", "english", "citizenship", "region"):
        for pk, pv in p.items():
            Wp = W * pv.to_numpy()[:, None]
            den = Wp.sum(0)
            for lvl in sorted(d[c].dropna().unique()):
                m = (d[c] == lvl).to_numpy()
                sh = Wp[m].sum(0) / den
                se = float(np.sqrt(4 / 80 * ((sh[1:] - sh[0]) ** 2).sum()))
                rows.append(dict(scenario=sc, overlap=pk, characteristic=c, level=lvl, share=float(sh[0]), se=se,
                                 weighted=float(Wp[m, 0].sum()), n_records=int((m & (pv > 0).to_numpy()).sum())))
res = pd.DataFrame(rows)
ck.true("shares sum to 1", np.allclose(res.groupby(["scenario", "overlap", "characteristic"]).share.sum(), 1))
cen = res[res.overlap == "central"]
ck.true("enough survey records carry the central weight (>= 300 per scenario)",
        all(cen[(cen.scenario == s) & (cen.characteristic == "sex")].n_records.sum() >= 300 for s in cen.scenario.unique()))
# fragility: the central-scenario race and age shares should not move more than 10 points between the two overlap ends
w = res[(res.scenario == "mid") & res.characteristic.isin(["race_ethnicity", "age", "region"])].pivot_table(
    index=["characteristic", "level"], columns="overlap", values="share")
ck.true("mid: shares stable across overlap ends (|high - low| <= 0.10)", ((w["high"] - w["low"]).abs() <= 0.10).all(),
        soft=True, detail=str((w["high"] - w["low"]).abs().max()))

for c, l, lid in [("race_ethnicity", "Black, non-Hispanic", "both_black"),
                  ("race_ethnicity", "Hispanic/Latino (any race)", "both_hispanic"),
                  ("race_ethnicity", "White, non-Hispanic", "both_white"),
                  ("sex", "Female", "both_female"),
                  ("age", "50-64", "both_age_50_64"),
                  ("age", "18/19-29", "both_age_19_29"),
                  ("work_past_12_months", "Did not work", "both_did_not_work"),
                  ("education", "Less than high school", "both_less_than_hs"),
                  ("education", "High school or GED", "both_hs"),
                  ("region", "Chicago", "both_chicago")]:
    for sc in res.scenario.unique():
        r = cen[(cen.scenario == sc) & (cen.characteristic == c) & (cen.level == l)].iloc[0]
        led.derived(f"prof_{lid}_{Y}_{sc}", r.share, "share",
                    f"weighted share '{l}' among people likely to lose both programs by Dec {Y} ({sc}; SE {r.se:.3f}); "
                    "PUMS weight x central chance of losing both", [f"ovl_both_central_{Y}_{sc}", "pums_cook_person_records"])
res.to_csv(OUT / "tables" / "pums_profiles_both.csv", index=False)
# side-by-side with the at-risk groups and all adults (mid)
prof = pd.read_csv(OUT / "tables" / "pums_profiles.csv")
side = prof[prof.group.isin(["all_adults_19_64", "medicaid_aca_like", "snap_adults_18_64"])].pivot_table(
    index=["characteristic", "level"], columns="group", values="share", sort=False)
side["lose_both_mid"] = cen[cen.scenario == "mid"].set_index(["characteristic", "level"]).share
side["lose_both_mid_se"] = cen[cen.scenario == "mid"].set_index(["characteristic", "level"]).se
side.to_csv(OUT / "tables" / "pums_profiles_both_wide.csv")
for (c, l), lid in {("race_ethnicity", "Black, non-Hispanic"): "black", ("age", "50-64"): "age_50_64",
                    ("work_past_12_months", "Did not work"): "did_not_work", ("region", "Chicago"): "chicago",
                    ("sex", "Female"): "female"}.items():
    led.derived(f"prof_all_adults_{lid}", float(side.loc[(c, l), "all_adults_19_64"]), "share",
                f"weighted share '{l}' among all PUMS Cook adults 19-64 (step 4b reference group)", ["pums_cook_person_records"])
pd.set_option("display.width", 220)
print((side * 100).round(1).to_string())
ck.finish()
led.save()
