"""Step 2d: Cook County zip (ZCTA) frame. Combines geography, ACS counts and HFS zip enrollment.

Cook portion of zips crossing the county line: population-weighted using 2020 tract pieces
(tract population x share of tract land area inside the ZCTA), summed over Cook tracts.
Chicago share of each ZCTA: land-area overlap with the City of Chicago boundary.

Outputs data/processed/zcta_cook.csv      one row per ZCTA touching Cook
        data/processed/cook_geo.gpkg      layers: zcta, county, chicago
        data/processed/county_shares.csv  Cook share of Illinois (population, noncitizens, SNAP households)
"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import PROC, RAW, load_params  # noqa: E402
from lib.tracer import flush, trace, tracers  # noqa: E402

STEP = "01d_geo_acs"
ck = Checks(STEP)
P = load_params()
TOL = P["verification"]["tolerances"]
COOK = "17031"
SLIVER = 0.005  # ZCTAs with <0.5% of their population in Cook are dropped (listed in output)

# ---- tract-based Cook share of each ZCTA ---------------------------------------------------
rel = pd.read_csv(RAW / "geo/tab20_zcta520_tract20_natl.txt", sep="|", dtype=str, encoding="utf-8-sig")
rel = rel[rel.GEOID_TRACT_20.str.startswith("17") & rel.GEOID_ZCTA5_20.notna()]
for c in ("AREALAND_PART", "AREALAND_TRACT_20"):
    rel[c] = rel[c].astype(float)
tr = pd.read_csv(RAW / "acs/acs5_2024_il_tracts.csv", dtype=str)
tr["tract"] = tr.state + tr.county + tr.tract
tr["pop"] = tr.B01003_001E.astype(float)
ck.equal("tract pop: no negative/missing (Census uses negatives for N/A)", int((tr["pop"] < 0).sum() + tr["pop"].isna().sum()), 0)
rel = rel.merge(tr[["tract", "pop"]], left_on="GEOID_TRACT_20", right_on="tract", how="left")
ck.true("every 2020 IL tract in relationship file has ACS population", rel["pop"].notna().mean() > 0.995, soft=True,
        detail=f"{rel['pop'].isna().sum()} tract pieces without population")
rel["pop"] = rel["pop"].fillna(0)
rel["piece_pop"] = rel["pop"] * (rel.AREALAND_PART / rel.AREALAND_TRACT_20.where(rel.AREALAND_TRACT_20 > 0))
rel["piece_pop"] = rel.piece_pop.fillna(0)
rel["is_cook"] = rel.GEOID_TRACT_20.str[:5].eq(COOK)
z = rel.groupby("GEOID_ZCTA5_20").agg(pop_tracts=("piece_pop", "sum"),
                                      pop_cook_tracts=("piece_pop", lambda s: s[rel.loc[s.index, "is_cook"]].sum()))
z["cook_share"] = (z.pop_cook_tracts / z.pop_tracts).fillna(0)
z = z[z.pop_cook_tracts > 0].reset_index().rename(columns={"GEOID_ZCTA5_20": "zcta"})
slivers = z[z.cook_share < SLIVER]
z = z[z.cook_share >= SLIVER].copy()
z["border"] = z.cook_share < 0.995

# ---- ACS ZCTA counts --------------------------------------------------------------------------
acs = pd.read_csv(RAW / "acs/acs5_2024_zcta.csv", dtype={"zcta": str})
acs = acs.assign(pop=acs.B01003_001E, hh_total=acs.B22003_001E, snap_hh=acs.B22003_002E,
                 mcd_19_64=acs.C27007_007E + acs.C27007_017E,
                 mcd_all=acs[[f"C27007_{i:03d}E" for i in (4, 7, 10, 14, 17, 20)]].sum(axis=1))
cols = ["pop", "hh_total", "snap_hh", "mcd_19_64", "mcd_all"]
z = z.merge(acs[["zcta"] + cols], on="zcta", how="left")
ck.no_nulls("every Cook ZCTA has ACS counts", z, cols)
for c in cols:
    z[c + "_cook"] = z[c] * z.cook_share

# ---- HFS enrollment by zip (USPS zip treated as ZCTA where codes match) ------------------------
h = pd.read_csv(PROC / "hfs_zip_fy2025.csv", dtype={"zip": str})
h["hfs_total"] = h[["children", "adults_disabled", "aca_adults", "other_adults", "seniors"]].sum(axis=1, min_count=1)
h = h.rename(columns={"zip": "zcta", "aca_adults": "hfs_aca"})
z = z.merge(h[["zcta", "hfs_aca", "hfs_total", "aca_adults_suppressed"]], on="zcta", how="left")
z["hfs_missing"] = z.hfs_aca.isna() & ~z.aca_adults_suppressed.fillna(False).astype(bool)
z[["hfs_aca", "hfs_total"]] = z[["hfs_aca", "hfs_total"]].fillna(0)  # '*' = small suppressed count -> 0
z["hfs_aca_cook"] = z.hfs_aca * z.cook_share
z["hfs_total_cook"] = z.hfs_total * z.cook_share

# Cook-area HFS zips with no ZCTA (PO-box / unique zips): their enrollees can't be mapped
cook_zip3 = {"600", "601", "604", "606", "607", "608"}
orphan = h[h.zcta.str[:3].isin(cook_zip3) & ~h.zcta.isin(set(acs.zcta))]

# ---- geometry and Chicago share -------------------------------------------------------------
zg = gpd.read_file(f"zip://{RAW / 'geo/cb_2020_us_zcta520_500k.zip'}")
zg = zg[zg.ZCTA5CE20.isin(z.zcta)][["ZCTA5CE20", "geometry"]].rename(columns={"ZCTA5CE20": "zcta"})
county = gpd.read_file(f"zip://{RAW / 'geo/cb_2024_us_county_500k.zip'}")
county = county[county.GEOID == COOK][["GEOID", "NAME", "geometry"]]
place = gpd.read_file(f"zip://{RAW / 'geo/cb_2024_17_place_500k.zip'}")
chicago = place[place.GEOID == "1714000"][["GEOID", "NAME", "geometry"]]
ck.equal("Chicago boundary found (GEOID 1714000)", len(chicago), 1)
ck.equal("Cook County boundary found", len(county), 1)
ck.equal("every Cook ZCTA has a shape", len(zg), len(z))

crs = 26916  # NAD83 / UTM 16N, metres
zp, cp = zg.to_crs(crs), chicago.to_crs(crs)
zp["chicago_share_area"] = zp.geometry.intersection(cp.geometry.iloc[0]).area / zp.geometry.area
z = z.merge(zp[["zcta", "chicago_share_area"]], on="zcta")
z["region"] = pd.cut(z.chicago_share_area, [-0.01, 0.5, 1.01], labels=["suburban Cook", "Chicago"]).astype(str)

# ---- checks against county totals -----------------------------------------------------------------
cty = pd.read_csv(RAW / "acs/acs5_2024_il_counties.csv", dtype={"county": str}).set_index("county")
cook_pop = cty.loc["031", "B01003_001E"]
ck.close("Cook pop: sum of ZCTA Cook portions vs ACS county total", z.pop_cook.sum(), cook_pop,
         rel_tol=TOL["zcta_cook_pop_vs_county_rel"])
ck.close("Cook pop: tract pieces vs ACS county total (should be ~exact)", z.pop_cook_tracts.sum(), cook_pop, rel_tol=0.001)
ck.close("Cook SNAP households: ZCTA Cook portions vs county total", z.snap_hh_cook.sum(),
         cty.loc["031", "B22003_002E"], rel_tol=0.03)
hfs_cook = z.hfs_aca_cook.sum()
ck.close("HFS ACA: zip file Cook portion vs HFS county page (364,204)", hfs_cook,
         P["verification"]["anchors"]["hfs_cook_aca_fy2025"], rel_tol=0.03, soft=True,
         detail=f"orphan Cook-area zips (no ZCTA): {len(orphan)} with {orphan.hfs_aca.sum():,.0f} ACA adults")
ck.close("HFS ACA: zip file Cook portion within 6% of county page", hfs_cook,
         P["verification"]["anchors"]["hfs_cook_aca_fy2025"], rel_tol=0.06)
ck.between("Chicago ZCTA count plausible (~55-65)", (z.region == "Chicago").sum(), 50, 70)
for c in ("cook_share", "chicago_share_area"):
    ck.between(f"{c} within [0,1]", z[c].max(), 0, 1.0000001)

# ---- county shares (Cook / Illinois) --------------------------------------------------------------
sh = pd.DataFrame([
    dict(measure="population", cook=cook_pop, illinois=cty.B01003_001E.sum()),
    dict(measure="noncitizens", cook=cty.loc["031", "B05001_006E"], illinois=cty.B05001_006E.sum()),
    dict(measure="snap_households", cook=cty.loc["031", "B22003_002E"], illinois=cty.B22003_002E.sum()),
])
sh["cook_share"] = sh.cook / sh.illinois
sh["source_ref"] = "acs/acs5_2024_il_counties.csv (ACS 2020-2024 5-year)"
ck.between("Cook share of IL population ~40%", sh.set_index("measure").loc["population", "cook_share"], 0.38, 0.42)

# ---- save -------------------------------------------------------------------------------------
z = z.sort_values("zcta")
z.to_csv(PROC / "zcta_cook.csv", index=False)
slivers.to_csv(PROC / "zcta_cook_slivers_dropped.csv", index=False)
orphan.to_csv(PROC / "hfs_cook_area_zips_without_zcta.csv", index=False)
sh.to_csv(PROC / "county_shares.csv", index=False)
gpkg = PROC / "cook_geo.gpkg"
zg.merge(z[["zcta", "region", "cook_share", "border"]], on="zcta").to_file(gpkg, layer="zcta", driver="GPKG")
county.to_file(gpkg, layer="county", driver="GPKG")
chicago.to_file(gpkg, layer="chicago", driver="GPKG")

for zz in tracers()["zips"]:
    r = z[z.zcta == zz]
    if ck.true(f"tracer zip {zz} in Cook frame", len(r) == 1):
        r = r.iloc[0]
        for k in ("cook_share", "region", "pop", "snap_hh", "mcd_19_64", "hfs_aca_cook"):
            trace(STEP, f"zip:{zz}", k, r[k] if isinstance(r[k], str) else round(float(r[k]), 4),
                  "ACS 2020-24 / tract-weighted Cook share / HFS FY2025")
flush(STEP)

print(f"Cook ZCTAs: {len(z)} ({(z.region == 'Chicago').sum()} Chicago, {z.border.sum()} border), "
      f"slivers dropped: {len(slivers)}, orphan HFS zips: {len(orphan)}")
print(f"HFS ACA Cook portion from zip file: {hfs_cook:,.0f} vs county page 364,204")
print(sh.to_string(index=False))
ck.finish()
