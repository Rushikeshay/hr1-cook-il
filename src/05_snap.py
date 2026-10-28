"""Step 6: Cook County SNAP. People lost, federal benefits lost, cuts for people still enrolled, new state costs.

People off SNAP because of H.R. 1 (residence basis = office series x snap_residence_adj, see step 3):
  wave 1 (observed)  drop beyond the pre-H.R. 1 trend, from each scenario's attribution start to Sept 2026 (step 3),
                     then held flat (caseload projection: flat from the latest month). Includes the April 2026
                     noncitizen cut and the May 2026 time-limit cutoffs; the noncitizen estimate is an "of which".
  wave 2 (Apr 2027)  new 36-month period: time-limited adults get 3 countable months Jan-Mar 2027, cutoffs Apr 1.
                     rate = first-wave excess drop (calibration window) / time-limited pool in Apr 2026
                     wave 2 = rate x multiplier x time-limited pool in Mar 2027 (same PUMS share, projected caseload)
Dollars (all federal, bucket 1): person-months lost x average benefit.
Out of scope (user decision 2026-10-28; see methods.md): benefit cuts for people who stay on SNAP from the LIHEAP/SUA
and internet rules: small next to coverage losses. The LIHEAP per-household cut is still computed for reference.
New state costs (bucket 3, Cook share): admin 75% from Oct 2026; benefit cost share 15% from FY2029 (early) or
FY2030 (late). SNAP has no bucket 2 (benefits are 100% federal). Buckets are never summed.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, load_params  # noqa: E402
from lib.ledger import Ledger, load  # noqa: E402
from lib.tracer import flush, trace, tracers  # noqa: E402

STEP = "05_snap"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
SP, TL = P["snap"], P["snap"]["time_limit"]
SC = P["meta"]["scenarios"]
YEARS = P["meta"]["analysis_years"]
L = load().set_index("id")
v = lambda i: float(L.loc[i, "value"])  # noqa: E731  value from an earlier step's ledger entry

cf = pd.read_csv(OUT / "tables" / "snap_counterfactual.csv")
cf["period"] = pd.PeriodIndex(cf.month, freq="M")
cf = cf.set_index("period")
BASE, LATEST = cf.index.min(), cf.index.max()
lt = LATEST.strftime("%Y_%m")
MONTHS = pd.period_range(BASE + 1, f"{YEARS[-1]}-12", freq="M")
adj = {sc: v(f"snap_residence_adj_{sc}") for sc in SC}
START = {sc: pd.Period(SP["attribution_start"][sc]["value"], "M") for sc in SC}

# ---- wave 1: observed H.R. 1 losses (office basis), as in step 3 -------------------------------------------
wave1 = {}
for sc in SC:
    if sc == "high":  # flat counterfactual from the Sept 2025 baseline
        s = cf.loc[BASE, "observed"] - cf.observed
    else:
        s = -cf.excess_change.where(cf.index >= START[sc], 0).fillna(0).cumsum()
    wave1[sc] = s.reindex(MONTHS).ffill()  # held flat after the latest month
    ck.close(f"[{sc}] wave 1 at {LATEST} x residence adj = step 3 ledger", wave1[sc][LATEST] * adj[sc],
             v(f"snap_hr1_persons_lost_to_{lt}_{sc}"), abs_tol=1)

# ---- wave 2: calibrated to the first-wave excess drop ------------------------------------------------------------
share_tl = v("snap_time_limited_share")
win = [pd.Period(m, "M") for m in TL["calibration_window"]["value"]]
led.assumed("snap_calibration_window", win[0].year * 100 + win[0].month, "yyyymm (start)",
            "params.yaml:snap.time_limit.calibration_window")
pre_cut = win[0] - 1
led.observed(f"snap_cook_persons_{pre_cut.strftime('%Y_%m')}_office", cf.loc[pre_cut, "observed"], "people",
             "IDHS SNAP Data by Servicing Office (Cook subtotal)")


def calibrate(w0, w1):
    target = -cf.loc[w0:w1, "excess_change"].sum()
    pool = share_tl * cf.loc[w0 - 1, "observed"]
    return target, pool, target / pool


target, pool26, rate = calibrate(*win)
led.derived("snap_wave1_calibration_target_office", target, "people",
            f"sum of excess drop beyond mid trend, {win[0]}..{win[-1]} (office basis)",
            ["snap_trend_rate", "snap_calibration_window"])
led.derived("snap_time_limited_pool_2026_office", pool26, "people",
            f"snap_time_limited_share * snap_cook_persons_{pre_cut.strftime('%Y_%m')}_office",
            ["snap_time_limited_share", f"snap_cook_persons_{pre_cut.strftime('%Y_%m')}_office"])
rate = led.derived("snap_wave1_loss_rate", rate, "share",
                   "snap_wave1_calibration_target_office / snap_time_limited_pool_2026_office",
                   ["snap_wave1_calibration_target_office", "snap_time_limited_pool_2026_office"])
ck.close("calibration reproduces the observed first-wave drop (rate x pool = target)", rate * pool26, target, abs_tol=1e-6)
ck.between("first-wave loss rate is a valid share (0-1]", rate, 0.01, 1.0)

proj = cf.loc[LATEST, "observed"]  # flat caseload projection to Mar 2027
pools = {"refilled": led.derived("snap_time_limited_pool_2027_refilled_office", share_tl * proj, "people",
                                 f"snap_time_limited_share * snap_cook_persons_{lt} (caseload held flat; pool refills)",
                                 ["snap_time_limited_share", f"snap_cook_persons_{lt}"]),
         "survivors": led.derived("snap_time_limited_pool_2027_survivors_office", pool26 - target, "people",
                                  "snap_time_limited_pool_2026_office - snap_wave1_calibration_target_office (no new entrants)",
                                  ["snap_time_limited_pool_2026_office", "snap_wave1_calibration_target_office"])}
pools["midpoint"] = led.derived("snap_time_limited_pool_2027_midpoint_office", (pools["refilled"] + pools["survivors"]) / 2,
                                "people", "average of the refilled and survivors pools",
                                ["snap_time_limited_pool_2027_refilled_office", "snap_time_limited_pool_2027_survivors_office"])
pool27 = pools["refilled"]
cut2 = pd.Period(str(TL["second_wave_cutoff"]["value"])[:7], "M")
mult = TL["calibration_multipliers"]
wave2 = {}
for sc in SC:
    kind = TL["second_wave_pool"][sc]["value"]
    m = led.assumed(f"snap_calibration_multiplier_{sc}", mult[sc], "x", f"params.yaml:snap.time_limit.calibration_multipliers.{sc}")
    r = led.derived(f"snap_second_wave_loss_rate_{sc}", rate * m, "share", f"snap_wave1_loss_rate * snap_calibration_multiplier_{sc}",
                    ["snap_wave1_loss_rate", f"snap_calibration_multiplier_{sc}"])
    ck.between(f"[{sc}] second-wave loss rate <= 1", r, 0, 1)
    w2 = led.derived(f"snap_second_wave_persons_{sc}", r * pools[kind] * adj[sc], "people",
                     f"snap_second_wave_loss_rate_{sc} * snap_time_limited_pool_2027_{kind}_office * snap_residence_adj_{sc}",
                     [f"snap_second_wave_loss_rate_{sc}", f"snap_time_limited_pool_2027_{kind}_office", f"snap_residence_adj_{sc}"])
    ck.true(f"[{sc}] wave 2 <= its pool", w2 <= pools[kind] * adj[sc])
    wave2[sc] = pd.Series([w2 if p >= cut2 else 0.0 for p in MONTHS], index=MONTHS)

# sensitivity: calibration window
sens = []
for label, w in (("May only", ("2026-05", "2026-05")), ("May-Sept", ("2026-05", str(LATEST)))):
    t_, p_, r_ = calibrate(pd.Period(w[0], "M"), pd.Period(w[1], "M"))
    sens.append(dict(calibration_window=f"{label}, pool = refilled", target_office=t_, pool_2026_office=p_,
                     loss_rate=r_, second_wave_mid_residence=r_ * pool27 * adj["mid"], valid=r_ <= 1))
for kind, pl in pools.items():  # pool choice, May-June window
    sens.append(dict(calibration_window=f"May-June, pool = {kind}", target_office=target, pool_2026_office=pool26,
                     loss_rate=rate, second_wave_mid_residence=rate * pl * adj["mid"], valid=True))
sens = pd.DataFrame(sens)

# ---- noncitizen cut (of which, inside wave 1) --------------------------------------------------------------------
nc_state = led.from_params("snap_noncitizen_statewide_loss", "snap.noncitizen.statewide_loss", "people")
acs_nc = v("acs_cook_noncitizen_share")
nc_month = pd.Period(str(SP["noncitizen"]["effective_date"]["value"])[:7], "M")
nc = {}
for sc in SC:
    node = SP["noncitizen"]["cook_share"][sc]
    if node["value"] == "from_acs_noncitizen_share":
        s_ = led.derived(f"snap_noncitizen_cook_share_{sc}", acs_nc, "share", "acs_cook_noncitizen_share",
                         ["acs_cook_noncitizen_share"])
    else:
        s_ = led.from_params(f"snap_noncitizen_cook_share_{sc}", "snap.noncitizen.cook_share", "share", scenario=sc)
    nc[sc] = led.derived(f"snap_noncitizen_loss_cook_{sc}", nc_state * s_, "people",
                         f"snap_noncitizen_statewide_loss * snap_noncitizen_cook_share_{sc} (of which, inside wave 1)",
                         ["snap_noncitizen_statewide_loss", f"snap_noncitizen_cook_share_{sc}"])
    ck.true(f"[{sc}] noncitizen cut fits inside wave 1 at {nc_month}", nc[sc] <= wave1[sc][nc_month] * adj[sc], soft=True)

# ---- dollars and state costs ---------------------------------------------------------------------------------------
avg = led.from_params("snap_avg_benefit_person_month", "snap.dollars.avg_benefit_person_month", "USD per person-month")
cty = pd.read_csv(PROC / "snap_county_2025_09.csv").set_index("county").persons
led.observed("snap_il_persons_county_pdf_2025_09", cty.sum(), "people", "IDHS SNAP Individual Counts by Counties, Sept 2025 (sum of 102 counties)")
ck.equal("county PDF has 102 Illinois counties", len(cty), 102)
cook_share = led.derived("snap_cook_share_il", cty["Cook"] / cty.sum(), "share",
                         "snap_cook_persons_county_pdf_2025_09 / snap_il_persons_county_pdf_2025_09",
                         ["snap_cook_persons_county_pdf_2025_09", "snap_il_persons_county_pdf_2025_09"])
admin_y = led.from_params("snap_admin_statewide_annual", "snap.state_cost_share.admin_state_share.statewide_annual_cost_increase", "USD per year")
admin_start = pd.Period(str(SP["state_cost_share"]["admin_state_share"]["effective_date"])[:7], "M")
cs_rate = led.from_params("snap_benefit_cost_share", "snap.state_cost_share.benefit_share_if_error_ge_10pct", "share")
cs_start = {k: pd.Period(str(n["value"])[:7], "M") for k, n in SP["state_cost_share"]["start_scenarios"].items()}
liheap = SP["benefit_cuts_still_enrolled"]["liheap_sua"]
# per-household cut from the IDHS utility standards (verified against the raw IDHS pages)
BRR = led.from_params("snap_benefit_reduction_rate", "snap.benefit_cuts_still_enrolled.liheap_sua.benefit_reduction_rate", "share")
std_pages = {"fy2026": "idhs/mr_25_33_utility_standards_2025_10.html", "fy2027": "idhs/wag_25_03_02_snap_standards.html"}
from lib.common import RAW  # noqa: E402
liheap_rows = []
for fy, node in liheap["utility_standards"].items():
    page = (RAW / std_pages[fy]).read_text(encoding="utf-8", errors="replace")
    for k in ("ac_heat", "limited", "single", "telephone"):
        ck.true(f"IDHS {fy} {k} standard ${node[k]} appears in {std_pages[fy]}", f"${node[k]}" in page)
        led.observed(f"snap_sua_{k}_{fy}", node[k], "USD per month", node["source"])
    for sc in SC:
        fb = liheap["fallback_standard"][sc]["value"]
        cut = led.derived(f"snap_liheap_cut_per_household_{fy}_{sc}", BRR * (node["ac_heat"] - node[fb]), "USD per household-month",
                          f"snap_benefit_reduction_rate * (snap_sua_ac_heat_{fy} - snap_sua_{fb}_{fy}); upper bound (50% rule, $769 cap)",
                          ["snap_benefit_reduction_rate", f"snap_sua_ac_heat_{fy}", f"snap_sua_{fb}_{fy}"])
        liheap_rows.append(dict(fiscal_year=fy, scenario=sc, fallback_standard=fb, cut_per_household_month=cut,
                                usd_per_year_per_10k_households=cut * 12 * 10_000))
liheap_tab = pd.DataFrame(liheap_rows)

monthly, annual = [], []
for sc in SC:
    df = pd.DataFrame(index=MONTHS)
    df["wave1"] = wave1[sc] * adj[sc]
    df["wave2"] = wave2[sc]
    df["persons_off"] = df.wave1 + df.wave2
    df["of_which_noncitizen"] = [nc[sc] if p >= nc_month else 0.0 for p in MONTHS]
    observed = cf.observed.reindex(MONTHS).ffill() * adj[sc]               # observed, then held flat
    df["cook_snap_persons"] = observed - df.wave2                           # projected caseload (residence)
    df["federal_benefits_lost_usd"] = df.persons_off * avg                  # bucket 1
    df["state_admin_cost_usd"] = [admin_y / 12 * cook_share if p >= admin_start else 0.0 for p in MONTHS]  # bucket 3
    for k, st in cs_start.items():
        df[f"state_benefit_share_{k}_usd"] = [df.cook_snap_persons[p] * avg * cs_rate if p >= st else 0.0 for p in MONTHS]
    ck.true(f"[{sc}] people off SNAP never exceed the Sept 2025 caseload", (df.persons_off <= cf.loc[BASE, "observed"] * adj[sc]).all())
    ck.non_negative(f"[{sc}] no negative values", df.stack())
    df.index.name = "month"
    monthly.append(df.reset_index().assign(month=lambda d: d.month.astype(str), scenario=sc))
    for y in [MONTHS[0].year] + YEARS:
        yr = df[df.index.year == y]
        row = dict(scenario=sc, year=y, months=len(yr), persons_off_dec=yr.persons_off.iloc[-1],
                   of_which_wave2_dec=yr.wave2.iloc[-1], person_months_lost=yr.persons_off.sum(),
                   federal_benefits_lost_usd=yr.federal_benefits_lost_usd.sum(),
                   state_admin_cost_usd=yr.state_admin_cost_usd.sum(),
                   **{f"state_benefit_share_{k}_usd": yr[f"state_benefit_share_{k}_usd"].sum() for k in cs_start})
        ins = [f"snap_hr1_persons_lost_to_{lt}_{sc}", f"snap_second_wave_persons_{sc}"]
        led.derived(f"snap_persons_off_dec_{y}_{sc}", row["persons_off_dec"], "people",
                    f"wave 1 (held flat after {LATEST}) + wave 2 (from {cut2}), end of Dec {y}", ins)
        pm = led.derived(f"snap_person_months_lost_{y}_{sc}", row["person_months_lost"], "person-months",
                         f"sum over {y} months of people off SNAP", ins)
        led.derived(f"snap_usd_federal_benefits_{y}_{sc}", row["federal_benefits_lost_usd"], "USD",
                    f"snap_person_months_lost_{y}_{sc} * snap_avg_benefit_person_month  [bucket 1]",
                    [f"snap_person_months_lost_{y}_{sc}", "snap_avg_benefit_person_month"])
        led.derived(f"snap_usd_state_admin_{y}_{sc}", row["state_admin_cost_usd"], "USD",
                    f"snap_admin_statewide_annual / 12 * snap_cook_share_il, months from {admin_start}  [bucket 3]",
                    ["snap_admin_statewide_annual", "snap_cook_share_il"])
        for k in cs_start:
            led.derived(f"snap_usd_state_benefit_share_{k}_{y}_{sc}", row[f"state_benefit_share_{k}_usd"], "USD",
                        f"Cook SNAP persons x snap_avg_benefit_person_month x snap_benefit_cost_share, from {cs_start[k]}  [bucket 3]",
                        ["snap_avg_benefit_person_month", "snap_benefit_cost_share", f"snap_second_wave_persons_{sc}"])
        ck.close(f"[{sc}] {y} federal $ = person-months x avg benefit", row["federal_benefits_lost_usd"], pm * avg, rel_tol=1e-9)
        annual.append(row)

mo = pd.concat(monthly, ignore_index=True)
an = pd.DataFrame(annual)
for y in YEARS:
    a = an[an.year == y].set_index("scenario")
    for col in ("persons_off_dec", "person_months_lost", "federal_benefits_lost_usd"):
        ck.ordered(f"{y} {col}: low <= mid <= high", *(a.loc[s, col] for s in SC))
ck.equal("no state benefit cost share before Oct 2028 (FY2029)",
         float(mo[mo.month < "2028-10"][[f"state_benefit_share_{k}_usd" for k in cs_start]].sum().sum()), 0.0)

# triangulation (informational)
tri = pd.DataFrame([
    dict(measure="Cook time-limited SNAP adults before the cutoffs (Apr 2026)", ours=pool26 * adj["mid"],
         external=TL["statewide_newly_time_limited"]["value"] * cook_share,
         external_source="IDHS via GCFD (Jul 2025): ~450k newly time-limited statewide x Cook share of IL SNAP",
         note="our PUMS exemption proxies are broad (disability, caregiver, student), so our pool is smaller; "
              "wave 2 is calibrated, so the pool size mostly cancels"),
    dict(measure="Cook first-wave time-limit losses (May-June 2026 excess)", ours=target * adj["mid"],
         external=SP["triangulation"]["statewide_work_req_losses_by_jun_2026"]["value"] * cook_share,
         external_source="IDHS (Sun-Times Jul 2026): ~148k statewide work-requirement losses by ~June 2026 x Cook share",
         note=""),
])
tri["ours_over_external"] = tri.ours / tri.external

tm = tracers()["month"]
r = mo[(mo.scenario == "mid") & (mo.month == tm)].iloc[0]
trace(STEP, f"month:{tm}", "mid: people off SNAP (residence)", round(r.persons_off), "wave 1 stock")
trace(STEP, f"office:{tracers()['office']}", "mid: projected Cook SNAP persons Dec 2028",
      round(mo[(mo.scenario == "mid") & (mo.month == f"{YEARS[-1]}-12")].cook_snap_persons.iloc[0]), "residence basis")
flush(STEP)
mo.to_csv(OUT / "tables" / "snap_model_monthly.csv", index=False)
an.to_csv(OUT / "tables" / "snap_annual.csv", index=False)
sens.to_csv(OUT / "tables" / "snap_wave2_sensitivity.csv", index=False)
tri.to_csv(OUT / "tables" / "snap_triangulation.csv", index=False)
liheap_tab.to_csv(OUT / "tables" / "snap_liheap_cut_per_household.csv", index=False)

pd.set_option("display.width", 220)
show = an.copy()
for c in [c for c in show if c.endswith("_usd")]:
    show[c] = (show[c] / 1e6).round(1)
print(show.round(0).to_string(index=False))
print(sens.round(3).to_string(index=False))
print(tri.drop(columns=["external_source", "note"]).round(2).to_string(index=False))
print(liheap_tab.round(2).to_string(index=False))
print(f"wave 1 rate {rate:.1%}; pool 2026 {pool26:,.0f}; pools 2027 " + ", ".join(f"{k} {v:,.0f}" for k, v in pools.items()))
ck.finish()
led.save()
