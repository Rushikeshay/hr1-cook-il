"""Step 8: story data bundle, map file, and static charts.

  output/story/story_data.json  every number the article uses. Headline numbers come from the ledger and keep their
                                 ledger id (fact-check: python src/trace.py <id>); time series come from step tables.
  output/story/cook_zcta.geojson Cook-clipped, simplified ZCTA shapes + Cook and Chicago outlines
  output/figures/*.png + .csv    static charts (social, print, methods) and the data behind each

Chart rules (dataviz skill): programs keep fixed hues (Medicaid = slot 1 blue, SNAP = slot 2 orange, both = slot 3
aqua); scenarios are ordered -> one-hue blue ramp; the three dollar buckets are separate panels (never summed);
Medicaid and SNAP maps are separate (adding their counts would double count people on both).
"""
import json
import sys
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, load_params  # noqa: E402
from lib.ledger import load  # noqa: E402

STEP = "07_outputs"
ck = Checks(STEP)
P = load_params()
SC = P["meta"]["scenarios"]
YEARS = P["meta"]["analysis_years"]
STORY = OUT / "story"
FIG = OUT / "figures"
STORY.mkdir(parents=True, exist_ok=True)
L = load().set_index("id")
T = OUT / "tables"


def num(i):
    """A ledger number with its provenance, for the bundle."""
    r = L.loc[i]
    return {"id": i, "v": float(r.value), "unit": r.unit, "label": r.label}


def lv(i):
    return float(L.loc[i, "value"])


# ---------------------------------------------------------------- bundle
mcd_an = pd.read_csv(T / "medicaid_annual.csv")
snp_an = pd.read_csv(T / "snap_annual.csv")
ovl = pd.read_csv(T / "medicaid_snap_overlap.csv")
headline = {}
for sc in SC:
    for y in YEARS:
        k = f"{y}_{sc}"
        headline[k] = {
            "medicaid_off": num(f"mcd_off_coverage_dec_{y}_{sc}"),
            "snap_off": num(f"snap_persons_off_dec_{y}_{sc}"),
            "both": num(f"ovl_both_central_{y}_{sc}"),
            "both_low": num(f"ovl_both_low_{y}_{sc}"),
            "both_high": num(f"ovl_both_high_{y}_{sc}"),
            "only_medicaid": num(f"ovl_only_medicaid_{y}_{sc}"),
            "only_snap": num(f"ovl_only_snap_{y}_{sc}"),
            "unique_residents": num(f"ovl_unique_residents_{y}_{sc}"),
            # bucket 1: federal dollars lost (Medicaid + SNAP may be added: same bucket)
            "b1_federal_medicaid": num(f"mcd_usd_federal_countycare_{y}_{sc}"),
            "b1_federal_snap": num(f"snap_usd_federal_benefits_{y}_{sc}"),
            # bucket 2: state dollars withdrawn as a direct result of H.R. 1
            "b2_state_medicaid": num(f"mcd_usd_state_countycare_{y}_{sc}"),
            # bucket 3: new state costs, Cook share
            "b3_snap_admin": num(f"snap_usd_state_admin_{y}_{sc}"),
            "b3_snap_benefit_share_early": num(f"snap_usd_state_benefit_share_early_{y}_{sc}"),
            "b3_snap_benefit_share_late": num(f"snap_usd_state_benefit_share_late_{y}_{sc}"),
        }
        o = ovl[(ovl.scenario == sc) & (ovl.year == y)].iloc[0]
        ck.close(f"[{sc} {y}] bundle unique residents = overlap table", headline[k]["unique_residents"]["v"],
                 o.unique_residents, abs_tol=0.5)

snap_hist = pd.read_csv(PROC / "snap_cook_monthly.csv")
cf = pd.read_csv(T / "snap_counterfactual.csv")
base_m, rate = pd.Period("2025-09", "M"), lv("snap_trend_rate")
base_v = float(snap_hist.set_index("month").loc["2025-09", "persons"])
snap_hist["trend"] = [base_v * (1 + rate) ** (pd.Period(m, "M") - base_m).n for m in snap_hist.month]
snap_series = snap_hist[["month", "persons", "trend", "series_break"]].rename(columns={"persons": "observed"})
events = [{"month": "2025-07", "text": "H.R. 1 signed (Jul 4) and IDHS reporting change"},
          {"month": "2025-12", "text": "IDHS first applies the work requirement"},
          {"month": "2026-02", "text": "Time-limit clock starts (Feb 1)"},
          {"month": "2026-04", "text": "Noncitizen cut (Apr 1)"},
          {"month": "2026-05", "text": "First time-limit cutoffs (May 1)"}]

mcd_mo = pd.read_csv(T / "medicaid_monthly.csv")
snp_mo = pd.read_csv(T / "snap_model_monthly.csv")
monthly = []
for sc in SC:
    a = mcd_mo[mcd_mo.scenario == sc].set_index("month")
    b = snp_mo[snp_mo.scenario == sc].set_index("month")
    for m in sorted(set(a.index) | set(b.index)):
        row = {"month": m, "scenario": sc,
               "medicaid_off": float(a.off_coverage.get(m, 0.0)) if m in a.index else 0.0,
               "snap_off": float(b.persons_off.get(m, 0.0)) if m in b.index else 0.0}
        for c in ("noncitizen", "work_req", "paperwork", "renewal_6mo"):
            row[f"medicaid_{c}"] = float(a[f"off_{c}"].get(m, 0.0)) if m in a.index else 0.0
        monthly.append(row)

zr = pd.read_csv(T / "zip_results_long.csv", dtype={"zcta": str})
zw = pd.read_csv(T / f"zip_results_{YEARS[-1]}_mid.csv", dtype={"zcta": str}).set_index("zcta")
zips = []
for z, r in zw.iterrows():
    d = {"zcta": z, "region": r.region, "border": bool(r.border), "small_pop": bool(r.small_pop),
         "pop": round(float(r.pop_cook)), "cook_share": round(float(r.cook_share), 4)}
    for sc in SC:
        q = zr[(zr.zcta == z) & (zr.year == YEARS[-1]) & (zr.scenario == sc)]
        g = lambda prog, key, metric: float(q[(q.program == prog) & (q.key == key) & (q.metric == metric)].value.sum())  # noqa: E731
        d[sc] = {"medicaid_off": round(g("medicaid", "medicaid", "people_off_coverage_dec"), 1),
                 "snap_off": round(g("snap", "snap", "people_off_snap_dec"), 1),
                 "federal_usd": round(g("medicaid", "medicaid", "federal_usd") + g("snap", "snap", "federal_usd"))}
    zips.append(d)
for sc in SC:
    ck.close(f"[{sc}] zip Medicaid totals = county", sum(z[sc]["medicaid_off"] for z in zips),
             lv(f"mcd_off_coverage_dec_{YEARS[-1]}_{sc}"), rel_tol=1e-4)

prof = pd.read_csv(T / "pums_profiles.csv")
bundle = {
    "meta": {"built": datetime.now().isoformat(timespec="seconds"), "as_of": str(P["meta"]["as_of"]),
             "scenarios": SC, "years": YEARS,
             "note": "numbers carry ledger ids; trace any of them with: python src/trace.py <id>"},
    "headline": headline,
    "context": {k: num(k) for k in ("mcd_baseline_aca_adults", "mcd_subject_share_a", "mcd_subject_share_b",
                                    "snap_cook_persons_county_pdf_2025_09", "snap_trend_rate",
                                    "countycare_share_of_cook_aca", "county_fy2027_health_revenue_decline",
                                    "county_fy2027_obbba_hospital_fallout", "county_fy2027_health_fund_gap",
                                    "hfs_internal_wr_loss_low", "hfs_internal_wr_loss_high",
                                    "ers_snap_gdp_multiplier", "ers_snap_jobs_per_billion")},
    "snap_series": {"rows": snap_series.to_dict("records"), "events": events,
                    "base_month": "2025-09", "trend_rate": rate},
    "monthly": monthly,
    "zips": zips,
    "profiles": prof[["group", "characteristic", "level", "share", "se"]].to_dict("records"),
    "countycare": pd.read_csv(T / "countycare_pressure.csv").to_dict("records"),
    "county_forecast": pd.read_csv(T / "county_forecast_comparison.csv").to_dict("records"),
    "charity_care": pd.read_csv(T / "cch_charity_care_history.csv").to_dict("records"),
    "snap_local_economy": pd.read_csv(T / "snap_local_economy.csv").to_dict("records"),
    "il_vs_urban": pd.read_csv(T / "illinois_vs_urban_scenarios.csv").fillna("").to_dict("records"),
    "ledger": L.reset_index()[["id", "value", "unit", "label", "formula", "source"]].to_dict("records"),
}
(STORY / "story_data.json").write_text(json.dumps(bundle, separators=(",", ":"), default=str), encoding="utf-8")
size_kb = (STORY / "story_data.json").stat().st_size / 1024
ck.between("story_data.json size reasonable (< 1.5 MB)", size_kb, 10, 1536, detail=f"{size_kb:.0f} KB")

# ---------------------------------------------------------------- map file
g = gpd.read_file(PROC / "cook_geo.gpkg", layer="zcta").to_crs(4326)
cty = gpd.read_file(PROC / "cook_geo.gpkg", layer="county").to_crs(4326)
chi = gpd.read_file(PROC / "cook_geo.gpkg", layer="chicago").to_crs(4326)
g = gpd.clip(g, cty)
g["geometry"] = g.geometry.simplify(0.0005, preserve_topology=True)
g = g[["zcta", "region", "border", "geometry"]]
ck.equal("map has all 177 Cook ZCTAs", g.zcta.nunique(), 177)
outlines = pd.concat([cty.assign(name="Cook County")[["name", "geometry"]],
                      chi.assign(name="Chicago")[["name", "geometry"]]])
outlines["geometry"] = outlines.geometry.simplify(0.0005, preserve_topology=True)
feat = json.loads(g.to_json(drop_id=True))
feat["outlines"] = json.loads(outlines.to_json(drop_id=True))
txt = json.dumps(feat, separators=(",", ":"))
txt = __import__("re").sub(r"(-?\d+\.\d{5})\d+", r"\1", txt)  # 5 decimals ~ 1 m
(STORY / "cook_zcta.geojson").write_text(txt, encoding="utf-8")
geo_kb = (STORY / "cook_zcta.geojson").stat().st_size / 1024
ck.between("map file size reasonable (< 2 MB)", geo_kb, 50, 2048, detail=f"{geo_kb:.0f} KB")

# ---------------------------------------------------------------- static charts
INK, INK2, MUTED, GRID, AXIS, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"           # Medicaid, SNAP, both
RAMP = {"low": "#86b6ef", "mid": "#2a78d6", "high": "#184f95"}  # ordinal blue (250 / 450 / 600)
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 10, "axes.edgecolor": AXIS,
                     "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF,
                     "figure.facecolor": SURF, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True})
fmtk = matplotlib.ticker.FuncFormatter(lambda x, _: f"{x/1000:,.0f}K" if abs(x) >= 1000 else f"{x:,.0f}")
fmtm = matplotlib.ticker.FuncFormatter(lambda x, _: f"${x/1e9:,.1f}B" if abs(x) >= 1e9 else f"${x/1e6:,.0f}M")
SRC = "Source: analysis of IDHS, HFS, ACS PUMS, Urban Institute/RWJF; see methods.md"


def save(fig, name, df, title, subtitle):
    h = fig.get_figheight()  # place title/subtitle at fixed distances (inches) from the top, any figure height
    fig.text(0.01, 1 - 0.12 / h, title, ha="left", va="top", fontsize=13, fontweight="semibold", color=INK)
    fig.text(0.01, 1 - 0.42 / h, subtitle, ha="left", va="top", fontsize=9.5, color=INK2)
    fig.text(0.01, 0.01, SRC, ha="left", fontsize=7.5, color=MUTED)
    fig.savefig(FIG / f"{name}.png", dpi=200)
    plt.close(fig)
    df.to_csv(FIG / f"{name}.csv", index=False)


# 1. SNAP observed vs trend
fig, ax = plt.subplots(figsize=(9, 4.8))
fig.subplots_adjust(top=0.84, bottom=0.12, left=0.08, right=0.97)
x = pd.Series(pd.PeriodIndex(snap_series.month, freq="M").to_timestamp(), index=snap_series.index)
after = snap_series.month >= "2025-09"
ax.plot(x[after], snap_series.trend[after], color=MUTED, lw=2, solid_capstyle="round", label="Pre-H.R. 1 trend")
ax.plot(x, snap_series.observed, color=S2, lw=2, solid_capstyle="round", label="Observed (IDHS)")
ax.fill_between(x[after], snap_series.observed[after], snap_series.trend[after], color=S2, alpha=0.10, lw=0)
last = snap_series.iloc[-1]
ax.scatter([x.iloc[-1]], [last.observed], s=40, color=S2, edgecolor=SURF, linewidth=2, zorder=3)
ax.annotate(f"{last.observed/1000:,.0f}K, {pd.Period(last.month, 'M').strftime('%b %Y')}", (x.iloc[-1], last.observed),
            xytext=(-6, -16), textcoords="offset points", ha="right", color=INK, fontsize=9)
ax.annotate(f"{(last.trend-last.observed)/1000:,.0f}K below trend (office basis)", (x.iloc[-1], (last.trend + last.observed) / 2),
            xytext=(-8, 0), textcoords="offset points", ha="right", va="center", color=INK2, fontsize=9)
ax.yaxis.set_major_formatter(fmtk)
ax.set_ylim(500_000, 950_000)
ax.legend(frameon=False, loc="lower left", fontsize=9)
save(fig, "fig1_snap_observed_vs_trend", snap_series, "Cook County SNAP caseload fell far below its trend",
     "People on SNAP served by Cook County offices, monthly. Shaded: drop beyond the pre-H.R. 1 trend (office basis).")

# 2. Medicaid off coverage by scenario
fig, ax = plt.subplots(figsize=(9, 4.8))
fig.subplots_adjust(top=0.84, bottom=0.12, left=0.08, right=0.9)
mm = pd.DataFrame(monthly)
for sc in SC:
    d = mm[mm.scenario == sc]
    xx = pd.Series(pd.PeriodIndex(d.month, freq="M").to_timestamp(), index=d.index)
    ax.plot(xx, d.medicaid_off, color=RAMP[sc], lw=2, solid_capstyle="round")
    ax.annotate(f"{sc}: {d.medicaid_off.iloc[-1]/1000:,.0f}K", (xx.iloc[-1], d.medicaid_off.iloc[-1]), xytext=(6, 0),
                textcoords="offset points", va="center", color=INK, fontsize=9)
ax.yaxis.set_major_formatter(fmtk)
ax.set_xlim(pd.Timestamp("2026-07-01"), pd.Timestamp("2028-12-31"))
save(fig, "fig2_medicaid_off_coverage", mm[["month", "scenario", "medicaid_off", "medicaid_noncitizen", "medicaid_work_req",
                                            "medicaid_paperwork", "medicaid_renewal_6mo"]],
     "Cook adults off Medicaid because of H.R. 1, three scenarios",
     "People off coverage at the end of each month (ACA adults). Work requirement from Apr 2027; 6-month renewals from Oct 2027.")

# 3. Residents affected (Dec of last year): only Medicaid / both / only SNAP
y = YEARS[-1]
rows = [dict(scenario=sc, only_medicaid=headline[f"{y}_{sc}"]["only_medicaid"]["v"], both=headline[f"{y}_{sc}"]["both"]["v"],
             only_snap=headline[f"{y}_{sc}"]["only_snap"]["v"], unique=headline[f"{y}_{sc}"]["unique_residents"]["v"]) for sc in SC]
d3 = pd.DataFrame(rows)
fig, ax = plt.subplots(figsize=(9, 3.6))
fig.subplots_adjust(top=0.70, bottom=0.14, left=0.08, right=0.97)
yy = np.arange(len(SC))[::-1]
left = np.zeros(len(SC))
for col, colr, lab in (("only_medicaid", S1, "Lose Medicaid only"), ("both", S3, "Lose both"), ("only_snap", S2, "Lose SNAP only")):
    ax.barh(yy, d3[col], left=left, height=0.42, color=colr, edgecolor=SURF, linewidth=2, label=lab)
    left += d3[col].to_numpy()
for i, r in d3.iterrows():
    ax.annotate(f"{r['unique']/1000:,.0f}K residents", (left[i], yy[i]), xytext=(6, 0), textcoords="offset points",
                va="center", color=INK, fontsize=9)
ax.set_yticks(yy, [s.capitalize() for s in SC])
ax.xaxis.set_major_formatter(fmtk)
ax.grid(axis="y", visible=False)
ax.set_xlim(0, d3["unique"].max() * 1.18)
ax.legend(frameon=False, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=9)
save(fig, "fig3_residents_affected", d3, f"Different Cook residents losing Medicaid or SNAP, Dec {y}",
     "Each person counted once: people losing both programs are shown in the middle segment (central estimate).")

# 4. Dollars, three buckets as separate panels
rows = []
for sc in SC:
    h = headline[f"{y}_{sc}"]
    rows.append(dict(scenario=sc, b1_medicaid=h["b1_federal_medicaid"]["v"], b1_snap=h["b1_federal_snap"]["v"],
                     b2_state_medicaid=h["b2_state_medicaid"]["v"], b3_snap_admin=h["b3_snap_admin"]["v"],
                     b3_snap_benefit_share_early=h["b3_snap_benefit_share_early"]["v"]))
d4 = pd.DataFrame(rows)
fig, axs = plt.subplots(1, 3, figsize=(10, 4.2), gridspec_kw={"width_ratios": [1.4, 1, 1]})
fig.subplots_adjust(top=0.78, bottom=0.12, left=0.07, right=0.98, wspace=0.35)
xs = np.arange(len(SC))
panels = [("Federal dollars lost", [("b1_medicaid", S1, "Medicaid"), ("b1_snap", S2, "SNAP")]),
          ("State Medicaid dollars withdrawn", [("b2_state_medicaid", S1, "Medicaid (state 10%)")]),
          ("New state SNAP costs (Cook share)", [("b3_snap_admin", S2, "Admin 75%"),
                                                 ("b3_snap_benefit_share_early", S3, "Benefit share (if FY2029)")])]
for ax, (ttl, parts) in zip(axs, panels):
    bottom = np.zeros(len(SC))
    for col, colr, lab in parts:
        ax.bar(xs, d4[col], bottom=bottom, width=0.5, color=colr, edgecolor=SURF, linewidth=2, label=lab)
        bottom += d4[col].to_numpy()
    for i, val in enumerate(bottom):
        ax.annotate(fmtm(val, None), (xs[i], val), xytext=(0, 3), textcoords="offset points", ha="center",
                    fontsize=8.5, color=INK)
    ax.set_xticks(xs, [s.capitalize() for s in SC])
    ax.yaxis.set_major_formatter(fmtm)
    ax.set_title(ttl, fontsize=10, color=INK, loc="left")
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, bottom.max() * (1.55 if len(parts) > 1 else 1.2))
    if len(parts) > 1:
        ax.legend(frameon=False, fontsize=8, loc="upper left")
save(fig, "fig4_dollars_three_buckets", d4, f"Money tied to H.R. 1 in Cook County, {y}",
     "Three separate buckets, not added together. Medicaid dollars use CountyCare's ACA rate ($836 per member-month).")

# 5. Zip maps (mid, Dec last year): Medicaid and SNAP per 1,000 residents, side by side
gm = g.merge(zw.reset_index()[["zcta", "mcd_off_per_1000_residents", "snap_off_per_1000_residents", "small_pop"]], on="zcta")
fig, axs = plt.subplots(1, 2, figsize=(10, 6.2))
fig.subplots_adjust(top=0.86, bottom=0.05, left=0.01, right=0.99, wspace=0.02)
for ax, col, ttl, cmap in ((axs[0], "mcd_off_per_1000_residents", "Off Medicaid", "Blues"),
                           (axs[1], "snap_off_per_1000_residents", "Off SNAP", "Oranges")):
    vmax = float(gm[col].quantile(0.98))
    gm.plot(column=col, ax=ax, cmap=cmap, vmin=0, vmax=vmax, edgecolor=SURF, linewidth=0.3,
            missing_kwds={"color": "#f0efec", "edgecolor": SURF, "linewidth": 0.3}, legend=True,
            legend_kwds={"shrink": 0.5, "label": "per 1,000 residents", "orientation": "horizontal", "pad": 0.01})
    chi.boundary.plot(ax=ax, color=INK2, linewidth=0.9)
    ax.set_title(ttl, fontsize=10.5, color=INK, loc="left")
    ax.set_axis_off()
save(fig, "fig5_zip_maps_mid", gm.drop(columns="geometry"),
     f"Where the losses land: people per 1,000 residents, Dec {y} (mid scenario)",
     "Cook portion of each zip area. Outline: City of Chicago. Gray: under 1,000 residents (rate not shown).")

figs = sorted(p.name for p in FIG.glob("fig*_*.png"))
ck.equal("five static charts written", len(figs), 5)
print(f"story_data.json {size_kb:.0f} KB; cook_zcta.geojson {geo_kb:.0f} KB; figures: {figs}")
ck.finish()
