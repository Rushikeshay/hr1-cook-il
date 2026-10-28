"""Step 7: split county results across Cook County zip areas (ZCTAs, Cook portion only).

Allocation keys (each ZCTA's share of the Cook total; shares sum to 1, so zip totals equal county totals exactly):
  Medicaid  primary: HFS FY2025 ACA adults by zip (Cook portion)    alt: ACS C27007 Medicaid ages 19-64 (Cook portion)
  SNAP      primary: ACS B22003 SNAP households (Cook portion)
Every component (incl. noncitizen losses) is split by its program's key. Border ZCTAs keep their Cook portion
(tract-population weights, step 2) and are flagged. HFS zips with no ZCTA (PO boxes) can't be mapped; their ACA adults
are left out of the key, so their share goes to the mapped ZCTAs (count reported).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, load_params  # noqa: E402
from lib.ledger import Ledger, load  # noqa: E402
from lib.tracer import flush, trace, tracers  # noqa: E402

STEP = "06_zip_alloc"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
SC = P["meta"]["scenarios"]
YEARS = P["meta"]["analysis_years"]
L = load().set_index("id")
MIN_POP = 1000  # Cook residents; below this, per-resident rates are blanked

z = pd.read_csv(PROC / "zcta_cook.csv", dtype={"zcta": str})
orph = pd.read_csv(PROC / "hfs_cook_area_zips_without_zcta.csv", dtype={"zcta": str})
ck.equal("177 Cook ZCTAs", len(z), 177)
ck.unique("ZCTAs unique", z, ["zcta"])
KEYS = {"medicaid": "hfs_aca_cook", "medicaid_alt_acs": "mcd_19_64_cook", "snap": "snap_hh_cook"}
for k, c in KEYS.items():
    ck.non_negative(f"{k} key non-negative", z[c])
    z[f"share_{k}"] = z[c] / z[c].sum()
    ck.close(f"{k} shares sum to 1", z[f"share_{k}"].sum(), 1.0, abs_tol=1e-9)
led.observed("hfs_aca_orphan_zips", orph.hfs_aca.fillna(0).sum(), "people",
             "HFS FY2025 zip PDF: Cook-area zips with no ZCTA (PO boxes); not mappable")
ck.true("unmappable PO-box zips hold < 1% of Cook ACA adults", orph.hfs_aca.fillna(0).sum() < 0.01 * z.hfs_aca_cook.sum(),
        detail=f"{orph.hfs_aca.fillna(0).sum():,.0f} ACA adults in {len(orph)} zips")

# ---- county results to allocate (read from step tables, checked against the ledger) ----------------------------
mcd = pd.read_csv(OUT / "tables" / "medicaid_annual.csv")
snp = pd.read_csv(OUT / "tables" / "snap_annual.csv")
items = []  # (program, metric, year, scenario, county value, ledger id)
for r in mcd.itertuples():
    items += [("medicaid", "people_off_coverage_dec", r.year, r.scenario, r.off_coverage_dec, f"mcd_off_coverage_dec_{r.year}_{r.scenario}"),
              ("medicaid", "federal_usd", r.year, r.scenario, r.usd_federal_countycare, f"mcd_usd_federal_countycare_{r.year}_{r.scenario}"),
              ("medicaid", "state_usd", r.year, r.scenario, r.usd_state_countycare, f"mcd_usd_state_countycare_{r.year}_{r.scenario}")]
for r in snp[snp.year.isin(YEARS)].itertuples():
    items += [("snap", "people_off_snap_dec", r.year, r.scenario, r.persons_off_dec, f"snap_persons_off_dec_{r.year}_{r.scenario}"),
              ("snap", "federal_usd", r.year, r.scenario, r.federal_benefits_lost_usd, f"snap_usd_federal_benefits_{r.year}_{r.scenario}")]
bad = [i for *_, val, i in items if abs(val - float(L.loc[i, "value"])) > 1e-6 * max(1, abs(val))]
ck.equal("every county value matches its ledger entry", bad, [])

rows = []
for prog, metric, y, sc, val, lid in items:
    keys = ["medicaid", "medicaid_alt_acs"] if prog == "medicaid" else ["snap"]
    for k in keys:
        part = z[["zcta", "region", "border", "cook_share"]].copy()
        part["value"] = val * z[f"share_{k}"]
        part = part.assign(program=prog, key=k, metric=metric, year=y, scenario=sc, county_value=val, ledger_id=lid)
        rows.append(part)
zl = pd.concat(rows, ignore_index=True)

# ---- gates ------------------------------------------------------------------------------------------------------------
tot = zl.groupby(["key", "metric", "year", "scenario"]).agg(s=("value", "sum"), c=("county_value", "first"))
ck.true("zip totals sum to county totals exactly (every key/metric/year/scenario)",
        ((tot.s - tot.c).abs() <= 1e-6 * tot.c.abs().clip(lower=1)).all(), detail=f"{len(tot)} totals checked")
ck.non_negative("no negative zip values", zl.value)
pop = z.set_index("zcta").pop_cook
for prog, metric in (("medicaid", "people_off_coverage_dec"), ("snap", "people_off_snap_dec")):
    w = zl[(zl.program == prog) & (zl.metric == metric) & (zl.year == YEARS[-1]) & (zl.scenario == "high")]
    w = w.groupby("zcta").value.sum()
    ck.true(f"{prog}: high-scenario people lost never exceed zip Cook population", (w <= pop.reindex(w.index)).all())

# ---- headline wide table (mid, last year) + region roll-up ---------------------------------------------------------
y = YEARS[-1]
pick = lambda prog, key, metric: (zl[(zl.program == prog) & (zl.key == key) & (zl.metric == metric) & (zl.year == y)  # noqa: E731
                                     & (zl.scenario == "mid")].set_index("zcta").value)
wide = z[["zcta", "region", "border", "cook_share", "pop_cook", "hfs_aca_cook", "mcd_19_64_cook", "snap_hh_cook"]].set_index("zcta")
wide[f"mcd_people_off_dec_{y}"] = pick("medicaid", "medicaid", "people_off_coverage_dec")
wide[f"mcd_people_off_dec_{y}_alt_acs"] = pick("medicaid", "medicaid_alt_acs", "people_off_coverage_dec")
wide[f"mcd_federal_usd_{y}"] = pick("medicaid", "medicaid", "federal_usd")
wide[f"snap_people_off_dec_{y}"] = pick("snap", "snap", "people_off_snap_dec")
wide[f"snap_federal_usd_{y}"] = pick("snap", "snap", "federal_usd")
wide["mcd_off_per_1000_residents"] = wide[f"mcd_people_off_dec_{y}"] / wide.pop_cook * 1000
wide["snap_off_per_1000_residents"] = wide[f"snap_people_off_dec_{y}"] / wide.pop_cook * 1000
wide["federal_usd_per_resident"] = (wide[f"mcd_federal_usd_{y}"] + wide[f"snap_federal_usd_{y}"]) / wide.pop_cook
wide["small_pop"] = wide.pop_cook < MIN_POP  # per-resident rates are not meaningful (e.g. 60141 Hines VA campus)
for c in ("mcd_off_per_1000_residents", "snap_off_per_1000_residents", "federal_usd_per_resident"):
    wide.loc[wide.small_pop, c] = float("nan")
wide["key_diff_hfs_vs_acs_pct"] = (wide[f"mcd_people_off_dec_{y}"] / wide[f"mcd_people_off_dec_{y}_alt_acs"] - 1) * 100
wide = wide.reset_index()
# federal $ per resident adds two FEDERAL amounts (bucket 1 Medicaid + bucket 1 SNAP): same bucket, so summing is allowed.

reg = zl[(zl.key.isin(["medicaid", "snap"])) & (zl.scenario == "mid")].groupby(["region", "program", "metric", "year"]).value.sum()
reg = reg.reset_index()
for prog, metric in (("medicaid", "people_off_coverage_dec"), ("snap", "people_off_snap_dec")):
    for rg in ("Chicago", "suburban Cook"):
        v = reg[(reg.region == rg) & (reg.program == prog) & (reg.metric == metric) & (reg.year == y)].value.sum()
        led.derived(f"zip_{prog}_{metric}_{y}_mid_{rg.split()[0].lower()}", v, "people",
                    f"sum over {rg} ZCTAs of county value x ZCTA share ({KEYS[prog]})",
                    [f"{'mcd_off_coverage' if prog == 'medicaid' else 'snap_persons_off'}_dec_{y}_mid"])
corr = wide[["hfs_aca_cook", "mcd_19_64_cook"]].corr().iloc[0, 1]
ck.between("Medicaid keys agree (HFS ACA vs ACS 19-64 correlation >= 0.8)", corr, 0.8, 1.0, soft=True)

# ---- tracers -------------------------------------------------------------------------------------------------------------
for zz in tracers()["zips"]:
    r = wide[wide.zcta == zz].iloc[0]
    for col in (f"mcd_people_off_dec_{y}", f"snap_people_off_dec_{y}", f"mcd_federal_usd_{y}", f"snap_federal_usd_{y}"):
        trace(STEP, f"zip:{zz}", f"mid {col}", round(float(r[col])), f"{r.region}; border={r.border}")
        led.derived(f"zip_{zz}_{col}_mid", float(r[col]), "USD" if "usd" in col else "people",
                    f"county value x ZCTA {zz} share",
                    [f"{'mcd' if col.startswith('mcd') else 'snap'}_{'usd_federal_countycare' if col == f'mcd_federal_usd_{y}' else 'usd_federal_benefits' if col == f'snap_federal_usd_{y}' else 'off_coverage_dec' if col.startswith('mcd') else 'persons_off_dec'}_{y}_mid"])
flush(STEP)

zl.to_csv(OUT / "tables" / "zip_results_long.csv", index=False)
wide.to_csv(OUT / "tables" / f"zip_results_{y}_mid.csv", index=False)
reg.to_csv(OUT / "tables" / "region_results_mid.csv", index=False)

pd.set_option("display.width", 200)
print(reg[reg.year == y].round(0).to_string(index=False))
cols = ["zcta", "region", f"mcd_people_off_dec_{y}", f"snap_people_off_dec_{y}", "mcd_off_per_1000_residents",
        "snap_off_per_1000_residents", "federal_usd_per_resident"]
print(wide.sort_values("federal_usd_per_resident", ascending=False)[cols].head(10).round(1).to_string(index=False))
print(f"Medicaid key correlation HFS vs ACS: {corr:.3f}; border ZCTAs: {int(z.border.sum())}; "
      f"small-pop ZCTAs: {wide[wide.small_pop].zcta.tolist()}")
ck.finish()
led.save()
