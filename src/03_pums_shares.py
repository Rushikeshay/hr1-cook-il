"""Step 4: shares from ACS PUMS 2020-2024 (Cook County PUMAs), with replicate-weight standard errors.

Medicaid (ACA-adult-like universe; rules in src/lib/pums_rules.py, settings in params.yaml medicaid.pums_rules):
  (a) subject share   = not exempt / universe                       <- headline base for the loss rates
  (b) subject and not already compliant / universe  (hours, earnings, either)
  exempt share        = 1 - (a)                                     <- base for paperwork losses
SNAP: time-limited adults (18-64, no child <14, not exempt) as a share of Cook SNAP persons, and the share not
meeting the 80-hour rule; share of SNAP households with no member 60+ or disabled (LIHEAP/SUA change).
PUMS describes 2020-2024, i.e. before H.R. 1. Standard errors: ACS successive-difference replication,
SE = sqrt(4/80 * sum_r (est_r - est)^2), 80 replicate weights.
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
from lib.tracer import flush, trace, tracers  # noqa: E402

STEP = "03_pums_shares"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
TOL = P["verification"]["tolerances"]
YR = P["geography"]["pums_year"]
SRC_P = f"ACS PUMS {YR - 4}-{YR} 5-year, Illinois person file (csv_pil), Cook PUMAs"
SRC_H = f"ACS PUMS {YR - 4}-{YR} 5-year, Illinois housing file (csv_hil), Cook PUMAs"
REP = [f"PWGTP{i}" for i in range(1, 81)]
HREP = [f"WGTP{i}" for i in range(1, 81)]

p = pd.read_csv(RAW / f"pums/pums_{YR}_5yr_cook.csv", dtype=str)
h = pd.read_csv(RAW / f"pums/pums_{YR}_5yr_housing_cook.csv", dtype=str)
ck.equal("PUMS person file: 36 Cook PUMAs", p.PUMA.nunique(), 36)
ck.equal("PUMS housing file: 36 Cook PUMAs", h.PUMA.nunique(), 36)
ck.unique("person records unique on SERIALNO+SPORDER", p, ["SERIALNO", "SPORDER"])
ck.unique("housing records unique on SERIALNO", h, ["SERIALNO"])
ck.true("every person has a housing record", p.SERIALNO.isin(h.SERIALNO).all())
ck.no_nulls("person weights present", p, ["PWGTP"] + REP)

df = R.prepare(p, h)
W = df[["PWGTP"] + REP].astype(float).to_numpy()
rules = R.rules_from_params(P)


def total(mask):
    t = W[mask.to_numpy()].sum(0)
    return t[0], float(np.sqrt(4 / 80 * ((t[1:] - t[0]) ** 2).sum()))


def share(num, den):
    n, d = W[num.to_numpy()].sum(0), W[den.to_numpy()].sum(0)
    s = n / d
    return float(s[0]), float(np.sqrt(4 / 80 * ((s[1:] - s[0]) ** 2).sum())), int(num.sum()), float(n[0]), float(d[0])


# ---- anchors: PUMS weighted totals vs published ACS tables -------------------------------------------
n_rec = led.observed("pums_cook_person_records", len(p), "records", SRC_P)
led.observed("pums_cook_housing_records", len(h), "records", SRC_H)
cty = pd.read_csv(RAW / f"acs/acs5_{P['geography']['acs_year']}_il_counties.csv", dtype={"county": str}).set_index("county")
c27 = pd.read_csv(RAW / f"acs/acs5_{P['geography']['acs_year']}_cook_c27007.csv").iloc[0]
acs_pop = led.observed("acs_cook_pop", cty.loc["031", "B01003_001E"], "people", "ACS 2020-24 5-yr B01003_001E, Cook County")
acs_mcd = led.observed("acs_cook_medicaid_19_64", c27.C27007_007E + c27.C27007_017E, "people",
                       "ACS 2020-24 5-yr C27007_007E + C27007_017E (male + female 19-64 with Medicaid/means-tested), Cook")
acs_snap = led.observed("acs_cook_snap_households", cty.loc["031", "B22003_002E"], "households",
                        "ACS 2020-24 5-yr B22003_002E, Cook County")

pop = led.derived("pums_cook_pop_weighted", total(df.AGEP.notna())[0], "people", "sum PWGTP, Cook PUMAs",
                  ["pums_cook_person_records"])
ck.close("PUMS weighted Cook population vs ACS B01003", pop, acs_pop, rel_tol=TOL["pums_pop_vs_acs_rel"])
civ_noninst = (df.RELSHIPP != "37") & (df.MIL != "1")
mcd = led.derived("pums_cook_medicaid_19_64_weighted",
                  total(civ_noninst & df.AGEP.between(19, 64) & (df.HINS4 == "1"))[0], "people",
                  "sum PWGTP: age 19-64, HINS4=1, civilian noninstitutionalized", ["pums_cook_person_records"])
ck.close("PUMS Medicaid 19-64 vs ACS C27007", mcd, acs_mcd, rel_tol=TOL["pums_table_vs_acs_rel"])
hu = h[(h.TYPEHUGQ == "1") & (h.FS == "1")]
snap_hh = led.derived("pums_cook_snap_households_weighted", hu.WGTP.astype(float).sum(), "households",
                      "sum WGTP: housing units with FS=1", ["pums_cook_housing_records"])
ck.close("PUMS SNAP households vs ACS B22003", snap_hh, acs_snap, rel_tol=TOL["pums_table_vs_acs_rel"])

# ---- Medicaid shares: headline + sensitivities ----------------------------------------------------------
VARIANTS = {  # headline = params; each other row changes one thing (or, for plan_universe, two)
    "headline": {},
    # the student treatment NOT used in the headline
    **({"student_exempt": dict(half_time_student="exempt")} if rules["half_time_student"] == "compliant"
       else {"student_compliant": dict(half_time_student="compliant")}),
    "income_limit_138": dict(poverty_limit_pct=138),
    "child_rule_household": dict(child_rule="household"),
    "plan_universe": dict(poverty_limit_pct=138, child_rule="household"),  # PLAN.md item 1 as first written
    "citizens_only": {},
}
VARIANTS = {k: v for k, v in VARIANTS.items() if k == "headline" or {**rules, **v} != rules or k == "citizens_only"}
rows, flags = [], {}
for v, over in VARIANTS.items():
    f = R.medicaid_flags(df, {**rules, **over})
    if v == "citizens_only":
        f = f.mul(df.CIT != "5", axis=0).astype(bool)
    flags[v] = f
    u = f.universe
    cnt, cnt_se = total(u)
    rows.append(dict(program="medicaid", variant=v, measure="universe_weighted", estimate=cnt, se=cnt_se,
                     n_records=int(u.sum())))
    for m, num in (("subject_share_a", f.subject), ("exempt_share", f.exempt),
                   ("subject_noncompliant_share_b_hours", f.subject_noncompliant_hours),
                   ("subject_noncompliant_share_b_earnings", f.subject_noncompliant_earnings),
                   ("subject_noncompliant_share_b_either", f.subject_noncompliant_either)):
        est, se, n, _, _ = share(num, u)
        rows.append(dict(program="medicaid", variant=v, measure=m, estimate=est, se=se, n_records=n))

M = flags["headline"]
res = pd.DataFrame(rows)


def get(v, m, col="estimate"):
    return float(res[(res.variant == v) & (res.measure == m)][col].iloc[0])


for v in VARIANTS:
    a = get(v, "subject_share_a")
    ck.between(f"[{v}] share (a) within [0,1]", a, 0, 1)
    ck.close(f"[{v}] subject + exempt = 1", a + get(v, "exempt_share"), 1.0, abs_tol=1e-9)
    for c in ("hours", "earnings"):
        ck.true(f"[{v}] (b) either <= (b) {c} <= (a)",
                get(v, "subject_noncompliant_share_b_either") <= get(v, f"subject_noncompliant_share_b_{c}") <= a)

# per-exemption shares of the universe (overlapping) and "this is their only exemption"
ex_cols = [c for c in M.columns if c.startswith("ex_")]
n_ex = M[ex_cols].sum(axis=1)
ex_rows = []
for c in ex_cols:
    any_, any_se, n, _, _ = share(M[c], M.universe)
    only, only_se, _, _, _ = share(M[c] & (n_ex == 1), M.universe)
    ex_rows.append(dict(exemption=c[3:], share_of_universe=any_, se=any_se, only_exemption_share=only,
                        only_se=only_se, n_records=n))
ex_tab = pd.DataFrame(ex_rows).sort_values("share_of_universe", ascending=False)
ck.true("exemption shares: any-exemption share <= sum of individual shares",
        get("headline", "exempt_share") <= ex_tab.share_of_universe.sum() + 1e-9)

# ledger: headline Medicaid
rid = ["pums_cook_person_records"]
uni = led.derived("mcd_pums_universe_weighted", get("headline", "universe_weighted"), "people",
                  "sum PWGTP over ACA-adult-like universe (19-64, HINS4, no Medicare/SSI; "
                  f"income limit {rules['poverty_limit_pct']}, child rule {rules['child_rule']})", rid)
for m, lid in (("subject_share_a", "mcd_subject_share_a"), ("exempt_share", "mcd_exempt_share"),
               ("subject_noncompliant_share_b_either", "mcd_subject_share_b"),
               ("subject_noncompliant_share_b_hours", "mcd_subject_share_b_hours"),
               ("subject_noncompliant_share_b_earnings", "mcd_subject_share_b_earnings")):
    led.derived(lid, get("headline", m), "share", f"weighted {m} of mcd_pums_universe_weighted (PUMS, headline rules)",
                ["mcd_pums_universe_weighted"])
    led.derived(f"{lid}_se", get("headline", m, "se"), "share", "replicate-weight SE (80 SDR weights)", [lid])
for v in VARIANTS:
    if v != "headline":
        led.derived(f"mcd_subject_share_a_{v}", get(v, "subject_share_a"), "share",
                    f"share (a) under sensitivity '{v}'", ["pums_cook_person_records"])
ck.between("share (a) SE < 2 points", get("headline", "subject_share_a", "se"), 0, 0.02, soft=True)

# triangulation (not pass/fail): PUMS universe vs HFS enrollment
hfs = led.from_params("mcd_baseline_aca_adults", "medicaid.baseline_aca_adults", "people")
ratio = led.derived("mcd_pums_universe_vs_hfs", uni / hfs, "ratio", "mcd_pums_universe_weighted / mcd_baseline_aca_adults",
                    ["mcd_pums_universe_weighted", "mcd_baseline_aca_adults"])
ck.between("PUMS ACA-like universe is 60-110% of HFS ACA enrollment (ACS undercounts Medicaid)", ratio, 0.6, 1.1, soft=True)

# ---- SNAP ---------------------------------------------------------------------------------------------
S = R.snap_flags(df, rules["hours_test_weekly"])
snap_rows = []
on_cnt, on_se = total(S.on_snap)
snap_rows.append(dict(program="snap", variant="headline", measure="snap_persons_weighted", estimate=on_cnt, se=on_se,
                      n_records=int(S.on_snap.sum())))
tl_cnt, tl_cnt_se = total(S.time_limited)
snap_rows.append(dict(program="snap", variant="headline", measure="time_limited_persons_weighted", estimate=tl_cnt,
                      se=tl_cnt_se, n_records=int(S.time_limited.sum())))
for m, num in (("time_limited_share", S.time_limited), ("time_limited_not_working_share", S.time_limited_not_working)):
    est, se, n, _, _ = share(num, S.on_snap)
    snap_rows.append(dict(program="snap", variant="headline", measure=m, estimate=est, se=se, n_records=n))
ck.true("time-limited not working <= time-limited <= SNAP persons",
        S.time_limited_not_working.sum() <= S.time_limited.sum() <= S.on_snap.sum())

# SNAP households with no member 60+ and no member with a disability (candidates for the LIHEAP/SUA change)
hh = df.groupby("SERIALNO")[["hh_n_60plus", "hh_n_dis"]].first()
hu = hu.set_index("SERIALNO").join(hh)
HW = hu[["WGTP"] + HREP].astype(float).to_numpy()
no_ed = ((hu.hh_n_60plus == 0) & (hu.hh_n_dis == 0)).to_numpy()
sh = HW[no_ed].sum(0) / HW.sum(0)
no_ed_se = float(np.sqrt(4 / 80 * ((sh[1:] - sh[0]) ** 2).sum()))
snap_rows.append(dict(program="snap", variant="headline", measure="snap_households_no_elderly_disabled_share",
                      estimate=float(sh[0]), se=no_ed_se, n_records=int(no_ed.sum())))
res = pd.concat([res, pd.DataFrame(snap_rows)], ignore_index=True)

sg = lambda m, col="estimate": float(res[(res.program == "snap") & (res.measure == m)][col].iloc[0])  # noqa: E731
led.derived("snap_pums_persons_weighted", on_cnt, "people", "sum PWGTP, persons in housing units with FS=1", rid)
for m, lid in (("time_limited_share", "snap_time_limited_share"),
               ("time_limited_not_working_share", "snap_time_limited_not_working_share")):
    led.derived(lid, sg(m), "share", f"weighted {m} of snap_pums_persons_weighted (PUMS, pre-H.R. 1)",
                ["snap_pums_persons_weighted"])
    led.derived(f"{lid}_se", sg(m, "se"), "share", "replicate-weight SE (80 SDR weights)", [lid])
led.derived("snap_hh_no_elderly_disabled_share", sg("snap_households_no_elderly_disabled_share"), "share",
            "weighted share of SNAP households with no member 60+ and none with a disability",
            ["pums_cook_snap_households_weighted"])
led.derived("snap_hh_no_elderly_disabled_share_se", no_ed_se, "share", "replicate-weight SE",
            ["snap_hh_no_elderly_disabled_share"])
for m in ("time_limited_share", "time_limited_not_working_share", "snap_households_no_elderly_disabled_share"):
    ck.between(f"SNAP {m} within [0,1]", sg(m), 0, 1)

# triangulation: PUMS SNAP persons (avg 2020-24) vs IDHS Cook office series Sept 2025
idhs = pd.read_csv(PROC / "snap_cook_monthly.csv").set_index("month").persons
ck.between("PUMS SNAP persons within 60-120% of IDHS Cook Sept 2025 (ACS undercounts SNAP)",
           on_cnt / idhs["2025-09"], 0.6, 1.2, soft=True, detail=f"PUMS {on_cnt:,.0f} vs IDHS {idhs['2025-09']:,}")

# ---- tracer household -------------------------------------------------------------------------------------
serial = tracers().get("pums_serialno")
if not serial:  # deterministic pick: first household (sorted) with one subject and one exempt adult
    g = pd.DataFrame({"s": df.SERIALNO, "sub": M.subject, "ex": M.exempt}).groupby("s").sum()
    serial = sorted(g[(g["sub"] > 0) & (g["ex"] > 0)].index)[0]
    print(f"!! tracer household not set: picked {serial}; put it in params.yaml verification.tracers.pums_serialno")
hhm = df.SERIALNO == serial
ck.true(f"tracer household {serial} found", hhm.any())
for i in df.index[hhm]:
    r, f = df.loc[i], M.loc[i]
    tag = f"pums:{serial}-{r.SPORDER}"
    trace(STEP, tag, "person", f"age {int(r.AGEP)}, HINS4 {r.HINS4}, POVPIP {r.POVPIP}, DIS {r.DIS}, WKHP {r.WKHP}",
          f"weight {r.PWGTP}")
    status = ("not in universe" if not f.universe else "exempt: " + ",".join(c[3:] for c in ex_cols if f[c])
              if f.exempt else "subject, " + ("not compliant" if f.subject_noncompliant_either else "compliant"))
    trace(STEP, tag, "medicaid status", status, "headline rules")
    trace(STEP, tag, "snap status", "time-limited" if S.time_limited[i] else ("on SNAP" if S.on_snap[i] else "not on SNAP"))
flush(STEP)

# ---- save ----------------------------------------------------------------------------------------------------
res["moe90"] = 1.645 * res.se
res.to_csv(OUT / "tables" / "pums_shares.csv", index=False)
ex_tab.to_csv(OUT / "tables" / "pums_medicaid_exemptions.csv", index=False)
keep = ["SERIALNO", "SPORDER", "PUMA", "PWGTP"]
pd.concat([df[keep], M.add_prefix("mcd_"), S.add_prefix("snap_")], axis=1).to_csv(PROC / "pums_flags.csv", index=False)

pd.set_option("display.width", 160)
print(res.pivot_table(index="measure", columns="variant", values="estimate", sort=False).round(3).to_string())
print(ex_tab.round(3).to_string(index=False))
print(f"PUMS universe {uni:,.0f} vs HFS {hfs:,.0f} ({ratio:.0%}); SNAP persons {on_cnt:,.0f}")
ck.finish()
led.save()
