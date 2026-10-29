"""Step 4b: who is at risk. Weighted profiles of Cook adults in each at-risk group, ACS PUMS 2020-2024, with
replicate-weight standard errors. Same rules as step 4 (src/lib/pums_rules.py, params medicaid.pums_rules).

Groups: all Cook adults 19-64 (reference); Medicaid ACA-like adults; subject to the work requirement; subject and
not already working/earning enough; SNAP adults 18-64 (reference); SNAP time-limited; time-limited and not working.
These describe people AT RISK, from a survey taken before H.R. 1; no public data identifies who actually lost coverage.
Chicago vs suburban: each PUMA's Chicago share = population-weighted share of its tracts inside Chicago (tract share
from the ZCTA-tract relationship file x each ZCTA's Chicago area share, step 2); PUMAs >= 50% Chicago count as Chicago.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib import pums_rules as R  # noqa: E402
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, RAW, load_params  # noqa: E402
from lib.ledger import Ledger  # noqa: E402

STEP = "03b_profiles"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
YR = P["geography"]["pums_year"]
REP = [f"PWGTP{i}" for i in range(1, 81)]

p = pd.read_csv(RAW / f"pums/pums_{YR}_5yr_cook.csv", dtype=str)
h = pd.read_csv(RAW / f"pums/pums_{YR}_5yr_housing_cook.csv", dtype=str)
ck.true("profile variables present", {"SEX", "HISP", "RAC1P", "SCHL", "ENG", "LANX"} <= set(p.columns))
df = R.prepare(p, h)
rules = R.rules_from_params(P)
M = R.medicaid_flags(df, rules)
S = R.snap_flags(df, rules["hours_test_weekly"])
W = df[["PWGTP"] + REP].astype(float).to_numpy()

# ---- PUMA -> Chicago share ------------------------------------------------------------------------------------------
zt = pd.read_csv(RAW / "geo/tab20_zcta520_tract20_natl.txt", sep="|", dtype=str, encoding="utf-8-sig",
                 usecols=["GEOID_ZCTA5_20", "GEOID_TRACT_20", "AREALAND_PART"])
zt = zt[zt.GEOID_TRACT_20.str.startswith("17031") & zt.GEOID_ZCTA5_20.notna()]
zt["area"] = zt.AREALAND_PART.astype(float)
zc = pd.read_csv(PROC / "zcta_cook.csv", dtype={"zcta": str})[["zcta", "chicago_share_area"]]
zt = zt.merge(zc, left_on="GEOID_ZCTA5_20", right_on="zcta", how="left").fillna({"chicago_share_area": 0})
tr = zt.groupby("GEOID_TRACT_20").apply(lambda g: (g.area * g.chicago_share_area).sum() / g.area.sum() if g.area.sum() else 0,
                                        include_groups=False).rename("chi").reset_index()
pop = pd.read_csv(RAW / "acs/acs5_2024_il_tracts.csv", dtype=str)
pop["GEOID_TRACT_20"] = pop.state + pop.county + pop.tract
pop["pop"] = pop.B01003_001E.astype(float)
rel = pd.read_csv(RAW / "geo/2020_Census_Tract_to_2020_PUMA.txt", dtype=str, encoding="utf-8-sig")
rel = rel[(rel.STATEFP == "17") & (rel.COUNTYFP == "031")]
rel["GEOID_TRACT_20"] = rel.STATEFP + rel.COUNTYFP + rel.TRACTCE
rel = rel.merge(tr, on="GEOID_TRACT_20", how="left").merge(pop[["GEOID_TRACT_20", "pop"]], on="GEOID_TRACT_20", how="left")
rel = rel.fillna({"chi": 0, "pop": 0})
puma = rel.groupby("PUMA5CE").apply(lambda g: (g.chi * g["pop"]).sum() / g["pop"].sum(), include_groups=False).rename("chicago_share")
mixed = puma[(puma > 0.1) & (puma < 0.9)]
ck.true("PUMAs are clearly Chicago or suburban (none 10-90% Chicago)", len(mixed) == 0, soft=True,
        detail=f"mixed PUMAs: {mixed.round(2).to_dict()}")
df["region"] = np.where(df.PUMA.map(puma) >= 0.5, "Chicago", "suburban Cook")
chi_pop = W[(df.region == "Chicago").to_numpy(), 0].sum()
ck.between("PUMS Chicago population ~2.6-2.8M (ACS city ~2.7M)", chi_pop, 2.55e6, 2.85e6)

# ---- characteristics ---------------------------------------------------------------------------------------------------
age = df.AGEP
race = np.select([df.HISP != "01", df.RAC1P == "1", df.RAC1P == "2", df.RAC1P == "6"],
                 ["Hispanic/Latino (any race)", "White, non-Hispanic", "Black, non-Hispanic", "Asian, non-Hispanic"],
                 "Other or multiracial, non-Hispanic")
schl = pd.to_numeric(df.SCHL, errors="coerce")
hrs = df.WKHP.fillna(0).where(df.WKL == "1", 0)
CHAR = {
    "age": pd.cut(age, [17, 29, 39, 49, 64], labels=["18/19-29", "30-39", "40-49", "50-64"]).astype(str),
    "sex": df.SEX.map({"1": "Male", "2": "Female"}),
    "race_ethnicity": pd.Series(race, index=df.index),
    "education": pd.Series(np.select([schl <= 15, schl <= 17, schl <= 20], ["Less than high school", "High school or GED",
                                     "Some college or associate"], "Bachelor's or higher"), index=df.index),
    "work_past_12_months": pd.Series(np.select([hrs == 0, hrs < 20, hrs < 35], ["Did not work", "Worked under 20 hrs/wk",
                                               "Worked 20-34 hrs/wk"], "Worked 35+ hrs/wk"), index=df.index),
    "english": pd.Series(np.where(df.ENG.isin(["2", "3", "4"]), "Speaks English less than very well",
                                  "English only or very well"), index=df.index),
    "citizenship": pd.Series(np.where(df.CIT == "5", "Not a citizen", "Citizen"), index=df.index),
    "region": df.region,
}
GROUPS = {
    "all_adults_19_64": df.AGEP.between(19, 64) & (df.RELSHIPP != "37"),
    "medicaid_aca_like": M.universe,
    "medicaid_subject": M.subject,
    "medicaid_subject_not_working_enough": M.subject_noncompliant_either,
    "snap_adults_18_64": S.on_snap & df.AGEP.between(18, 64),
    "snap_time_limited": S.time_limited,
    "snap_time_limited_not_working": S.time_limited_not_working,
}
rows = []
for g, gm in GROUPS.items():
    den = W[gm.to_numpy()].sum(0)
    for c, s in CHAR.items():
        for lvl in sorted(s[gm].dropna().unique()):
            num = W[(gm & (s == lvl)).to_numpy()].sum(0)
            sh = num / den
            se = float(np.sqrt(4 / 80 * ((sh[1:] - sh[0]) ** 2).sum()))
            rows.append(dict(group=g, characteristic=c, level=lvl, share=float(sh[0]), se=se, moe90=1.645 * se,
                             weighted=float(num[0]), n_records=int((gm & (s == lvl)).sum()), group_weighted=float(den[0])))
prof = pd.DataFrame(rows)
tot = prof.groupby(["group", "characteristic"]).share.sum()
ck.true("each characteristic's shares sum to 1 within every group", np.allclose(tot, 1.0))
ck.true("every group has >= 300 survey records", all(int(gm.sum()) >= 300 for gm in GROUPS.values()),
        detail=str({g: int(gm.sum()) for g, gm in GROUPS.items()}))
ck.close("subject group weight matches step 4 share (a) x universe", float(W[M.subject.to_numpy(), 0].sum()),
         0.4809047537510618 * W[M.universe.to_numpy(), 0].sum(), rel_tol=1e-3)

# a few headline facts to the ledger
def get(g, c, l):  # noqa: E302
    return prof[(prof.group == g) & (prof.characteristic == c) & (prof.level == l)].iloc[0]


for g, c, l, lid in [("medicaid_subject", "work_past_12_months", "Worked 20-34 hrs/wk", "prof_mcd_subject_work_20_34"),
                     ("medicaid_subject", "work_past_12_months", "Worked 35+ hrs/wk", "prof_mcd_subject_work_35plus"),
                     ("medicaid_subject", "region", "Chicago", "prof_mcd_subject_chicago"),
                     ("medicaid_subject", "race_ethnicity", "Black, non-Hispanic", "prof_mcd_subject_black"),
                     ("medicaid_subject", "race_ethnicity", "Hispanic/Latino (any race)", "prof_mcd_subject_hispanic"),
                     ("medicaid_subject", "age", "50-64", "prof_mcd_subject_age_50_64"),
                     ("snap_time_limited", "race_ethnicity", "Black, non-Hispanic", "prof_snap_tl_black"),
                     ("snap_time_limited", "work_past_12_months", "Did not work", "prof_snap_tl_did_not_work")]:
    r = get(g, c, l)
    led.derived(lid, r.share, "share", f"weighted share '{l}' among PUMS {g} (SE {r.se:.3f})", ["pums_cook_person_records"])
prof.to_csv(OUT / "tables" / "pums_profiles.csv", index=False)
wide = prof.pivot_table(index=["characteristic", "level"], columns="group", values="share", sort=False)[list(GROUPS)]
wide.to_csv(OUT / "tables" / "pums_profiles_wide.csv")
pd.set_option("display.width", 250)
print((wide * 100).round(0).to_string())
print({g: int(gm.sum()) for g, gm in GROUPS.items()})
ck.finish()
led.save()
