"""Step 5: Cook County Medicaid (ACA adults) coverage lost to H.R. 1, monthly 2026-2028, people and dollars.

Components (new losses per month; a person lost stays off: no re-enrollment is modeled):
  noncitizen      statewide loss x Cook share, all on Oct 1 2026
  work_req        baseline x subject share (a) x loss rate, where the rate is set so work-req + paperwork losses
                  = Urban/RWJF Illinois work-requirement share of ALL ACA adults (18/29/42%). First renewals spread evenly over 12 months from
                  March 2027; each month's losses take effect the next month (30-day response window)
  paperwork       baseline x exempt share x paperwork-loss rate, same timing (exempt adults who fail to document)
  renewal_6mo     paperwork losses from renewing every 6 months instead of yearly (Urban/RWJF Illinois rate x
                  baseline; Urban's renewal and work-requirement shares are additive): each cohort's first 6-month
                  renewal, Sept 2027-Aug 2028, losses the next month; level then held (net of re-enrollment)
  verification    2028: baseline x subject share x added rate, spread over 2028 renewals
subject share (a) is reduced by the unmodeled-exemption share (SUD treatment, recent incarceration, former foster
youth): subject = share_a x (1 - unmodeled); exempt = 1 - subject.
Dollars: member-months lost x PMPM; federal 90% (bucket 1), state 10% (bucket 2). Kept separate, never summed.
Baseline (HFS June 2025) is held flat; PMPM (CountyCare 2027) is held flat for 2026-2028.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, load_params  # noqa: E402
from lib.ledger import Ledger, load  # noqa: E402
from lib.tracer import flush, trace  # noqa: E402

STEP = "04_medicaid"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
MP, WR = P["medicaid"], P["medicaid"]["work_requirement"]
SC = P["meta"]["scenarios"]
YEARS = P["meta"]["analysis_years"]
MONTHS = pd.period_range(f"{YEARS[0]}-01", f"{YEARS[-1]}-12", freq="M")
COMPONENTS = ["noncitizen", "work_req", "paperwork", "renewal_6mo", "verification"]

# ---- inputs -----------------------------------------------------------------------------------------------
base = led.from_params("mcd_baseline_aca_adults", "medicaid.baseline_aca_adults", "people")
ck.equal("baseline = HFS Cook ACA adults FY2025 anchor", base, float(P["verification"]["anchors"]["hfs_cook_aca_fy2025"]))
hfs = pd.read_csv(PROC / "hfs_cook_enrollment.csv")
ck.equal("baseline = parsed HFS page (ACA, FY2025)",
         float(hfs[(hfs.category == "ACA") & (hfs.fiscal_year == "FY2025")].enrollees.iloc[0]), base)

L = load().set_index("id")
share_a = float(L.loc["mcd_subject_share_a", "value"])
share_b = float(L.loc["mcd_subject_share_b", "value"])
unmod = led.from_params("mcd_unmodeled_exemptions_share", "medicaid.unmodeled_exemptions_share", "share")
subj = led.derived("mcd_subject_share_eff", share_a * (1 - unmod), "share",
                   "mcd_subject_share_a * (1 - mcd_unmodeled_exemptions_share)",
                   ["mcd_subject_share_a", "mcd_unmodeled_exemptions_share"])
exempt = led.derived("mcd_exempt_share_eff", 1 - subj, "share", "1 - mcd_subject_share_eff", ["mcd_subject_share_eff"])
n_subj = led.derived("mcd_subject_people", base * subj, "people", "mcd_baseline_aca_adults * mcd_subject_share_eff",
                     ["mcd_baseline_aca_adults", "mcd_subject_share_eff"])
led.derived("mcd_subject_noncompliant_people", base * share_b, "people",
            "mcd_baseline_aca_adults * mcd_subject_share_b (context: subject and not already working/earning enough)",
            ["mcd_baseline_aca_adults", "mcd_subject_share_b"])

# noncitizen Cook share: low = CBS 44%; mid/high = ACS Cook / Illinois noncitizens
cs = pd.read_csv(PROC / "county_shares.csv").set_index("measure")
led.observed("acs_cook_noncitizens", cs.loc["noncitizens", "cook"], "people", "ACS 2020-24 5-yr B05001_006E, Cook")
led.observed("acs_il_noncitizens", cs.loc["noncitizens", "illinois"], "people", "ACS 2020-24 5-yr B05001_006E, Illinois")
acs_nc = led.derived("acs_cook_noncitizen_share", cs.loc["noncitizens", "cook"] / cs.loc["noncitizens", "illinois"],
                     "share", "acs_cook_noncitizens / acs_il_noncitizens", ["acs_cook_noncitizens", "acs_il_noncitizens"])
nc_state = led.from_params("mcd_noncitizen_statewide_loss", "medicaid.noncitizen.statewide_loss", "people")

# PMPM: CountyCare ACA capitation / members / 12 (CCH FY27 deck p25)
cc = pd.read_csv(PROC / "cch_countycare_2027.csv").set_index("program").loc["ACA Adult"]
cap = led.observed("cch_aca_capitation_2027", cc.capitation_musd_2027 * 1e6, "USD", "CCH Prelim FY27 budget deck, page 25")
mem = led.observed("cch_aca_members_2027", cc.members_2027, "people", "CCH Prelim FY27 budget deck, page 25")
ck.equal("CCH inputs match params (capitation, members)", (cap, mem),
         tuple(float(v) for v in MP["dollars"]["pmpm_countycare_aca"]["inputs"].values()))
pmpm = {"countycare": led.derived("mcd_pmpm_countycare", cap / mem / 12, "USD per member-month",
                                  "cch_aca_capitation_2027 / cch_aca_members_2027 / 12",
                                  ["cch_aca_capitation_2027", "cch_aca_members_2027"])}
if MP["dollars"]["pmpm_hfs_statewide_aca"]["value"] is not None:
    pmpm["hfs"] = led.from_params("mcd_pmpm_hfs", "medicaid.dollars.pmpm_hfs_statewide_aca", "USD per member-month")
else:
    print("!! HFS statewide ACA PMPM not in params yet: dollars use the CountyCare PMPM only")
fed = led.from_params("mcd_federal_match_aca", "medicaid.dollars.federal_match_aca", "share")

# six-month renewal loss rates: Urban/RWJF Illinois, redeterminations only (parsed in 01f)
urb_in = pd.read_csv(PROC / "urban_il_2028.csv").set_index("scenario")
urban_redet = {s: led.observed(f"urban_il_2028_redet_pct_{s}", -r.redet_pct / 100, "share",
                               f"Urban/RWJF 2026, {r.source_ref} (six-month redeterminations only)")
               for s, r in urb_in.iterrows()}

urban_wr = {s: led.observed(f"urban_il_2028_work_req_pct_{s}", -r.work_req_pct / 100, "share",
                            f"Urban/RWJF 2026, {r.source_ref} (work requirements after six-month redeterminations)")
            for s, r in urb_in.iterrows()}
hfs_lo = led.from_params("hfs_internal_wr_loss_low", "medicaid.hfs_internal_estimate.low", "people")
hfs_hi = led.from_params("hfs_internal_wr_loss_high", "medicaid.hfs_internal_estimate.high", "people")
hfs_den = led.from_params("hfs_aca_adults_subject_statewide", "medicaid.hfs_internal_estimate.aca_adults_subject", "people")

# timing
first_renew = pd.Period(WR["first_renewals_checked"]["value"], "M")
spread = int(WR["initial_renewals_spread_months"]["value"])
lag = 1  # 30-day response window -> loss takes effect the next month
renew1 = pd.period_range(first_renew, periods=spread, freq="M")
cycle2_loss_start = first_renew + int(WR["renewal_months_per_cycle"]["value"]) + lag  # Sept 2027 renewals -> Oct
renew_6mo_loss_months = pd.period_range(cycle2_loss_start, periods=spread, freq="M")  # Oct 2027 - Sep 2028
renew_2028 = pd.period_range(f"{YEARS[-1]}-01", f"{YEARS[-1]}-12", freq="M")
nc_month = pd.Period(str(MP["noncitizen"]["statewide_loss"]["effective_date"])[:7], "M")
ck.equal("first work-requirement losses = params first_loss_month", str(renew1[0] + lag),
         str(WR["first_loss_month"]["value"])[:7])

# ---- model ----------------------------------------------------------------------------------------------------
monthly, annual = [], []
for sc in SC:
    paper = led.from_params(f"mcd_loss_rate_exempt_paperwork_{sc}", "medicaid.loss_rate_exempt_paperwork", "share", scenario=sc)
    lr = MP["loss_rate_subject"][sc]
    assert lr["value"] == "from_urban_il_work_req", "loss_rate_subject: only the Urban source is wired up"
    us = lr["urban_scenario"]
    # Urban: work-requirement losses (after renewals) as a share of ALL ACA adults; we split it into exempt paperwork
    # losses (our parameter) and subject-adult losses (the rest), so the total matches Urban.
    rate = led.derived(f"mcd_loss_rate_subject_{sc}", (urban_wr[us] * base - base * exempt * paper) / n_subj, "share",
                       f"(urban_il_2028_work_req_pct_{us} * mcd_baseline_aca_adults - paperwork losses) / mcd_subject_people",
                       [f"urban_il_2028_work_req_pct_{us}", "mcd_baseline_aca_adults", "mcd_exempt_share_eff",
                        f"mcd_loss_rate_exempt_paperwork_{sc}", "mcd_subject_people"])
    ck.between(f"[{sc}] derived subject loss rate is a valid share", rate, 0, 1)
    rn = MP["six_month_renewal_loss"][sc]
    assert rn["value"] == "from_urban_il_redet", "six_month_renewal_loss: only the Urban source is wired up"
    renew_rate = led.derived(f"mcd_renewal_6mo_loss_rate_{sc}", urban_redet[rn["urban_scenario"]], "share",
                             f"urban_il_2028_redet_pct_{rn['urban_scenario']} (Illinois rate applied to Cook)",
                             [f"urban_il_2028_redet_pct_{rn['urban_scenario']}"])
    verif = led.from_params(f"mcd_verification_increase_2028_{sc}", "medicaid.verification_increase_2028", "share", scenario=sc)
    node = MP["noncitizen"]["cook_share"][sc]
    if node["value"] == "from_acs_noncitizen_share":
        ncs = led.derived(f"mcd_noncitizen_cook_share_{sc}", acs_nc, "share", "acs_cook_noncitizen_share",
                          ["acs_cook_noncitizen_share"])
    else:
        ncs = led.from_params(f"mcd_noncitizen_cook_share_{sc}", "medicaid.noncitizen.cook_share", "share", scenario=sc)
    nc_cook = led.derived(f"mcd_noncitizen_loss_cook_{sc}", nc_state * ncs, "people",
                          f"mcd_noncitizen_statewide_loss * mcd_noncitizen_cook_share_{sc}",
                          ["mcd_noncitizen_statewide_loss", f"mcd_noncitizen_cook_share_{sc}"])
    wr_total = led.derived(f"mcd_work_req_loss_total_{sc}", n_subj * rate, "people",
                           f"mcd_subject_people * mcd_loss_rate_subject_{sc}", ["mcd_subject_people", f"mcd_loss_rate_subject_{sc}"])
    pw_total = led.derived(f"mcd_paperwork_loss_total_{sc}", base * exempt * paper, "people",
                           f"mcd_baseline_aca_adults * mcd_exempt_share_eff * mcd_loss_rate_exempt_paperwork_{sc}",
                           ["mcd_baseline_aca_adults", "mcd_exempt_share_eff", f"mcd_loss_rate_exempt_paperwork_{sc}"])
    vf_total = led.derived(f"mcd_verification_loss_2028_total_{sc}", n_subj * verif, "people",
                           f"mcd_subject_people * mcd_verification_increase_2028_{sc}",
                           ["mcd_subject_people", f"mcd_verification_increase_2028_{sc}"])

    new = pd.DataFrame(0.0, index=MONTHS, columns=COMPONENTS)
    if nc_month in new.index:
        new.loc[nc_month, "noncitizen"] = nc_cook
    for r in renew1:
        if r + lag in new.index:
            new.loc[r + lag, "work_req"] += wr_total / spread
            new.loc[r + lag, "paperwork"] += pw_total / spread
    for r in renew_2028:
        if r + lag in new.index:
            new.loc[r + lag, "verification"] += vf_total / len(renew_2028)
    stock = 0.0
    stocks = []
    for m in MONTHS:  # Urban's renewal and work-requirement shares are additive (work req is measured AFTER
        if m in renew_6mo_loss_months:  # renewals), so both apply to the baseline without double counting
            new.loc[m, "renewal_6mo"] = base * renew_rate / spread
        stock += new.loc[m].sum()
        stocks.append(stock)
    df = new.add_prefix("new_")
    df["off_coverage"] = stocks                       # people off coverage at end of month (cumulative)
    for c in COMPONENTS:
        df[f"off_{c}"] = new[c].cumsum()
    df["enrolled"] = base - df.off_coverage
    df["member_months_lost"] = df.off_coverage        # one month off coverage = one member-month lost
    for k, v in pmpm.items():
        df[f"usd_total_{k}"] = df.member_months_lost * v
        df[f"usd_federal_{k}"] = df[f"usd_total_{k}"] * fed
        df[f"usd_state_{k}"] = df[f"usd_total_{k}"] * (1 - fed)
    df.insert(0, "scenario", sc)
    df.index.name = "month"
    monthly.append(df.reset_index().assign(month=lambda d: d.month.astype(str)))

    ck.true(f"[{sc}] losses never exceed baseline", (df.off_coverage <= base).all() and (df.enrolled >= 0).all())
    ck.non_negative(f"[{sc}] no negative new losses", new.stack())
    ck.close(f"[{sc}] components sum to total off coverage", df[[f"off_{c}" for c in COMPONENTS]].iloc[-1].sum(),
             df.off_coverage.iloc[-1], abs_tol=1e-6)
    ck.close(f"[{sc}] all first-cycle work-req losses land by {renew1[-1] + lag}",
             df.loc[renew1[-1] + lag, "off_work_req"], wr_total, abs_tol=1e-6)

    inputs_common = ["mcd_baseline_aca_adults", f"mcd_work_req_loss_total_{sc}", f"mcd_paperwork_loss_total_{sc}",
                     f"mcd_noncitizen_loss_cook_{sc}", f"mcd_renewal_6mo_loss_rate_{sc}",
                     f"mcd_verification_loss_2028_total_{sc}"]
    for y in YEARS:
        yr = df[df.index.year == y]
        row = dict(scenario=sc, year=y, off_coverage_dec=yr.off_coverage.iloc[-1],
                   new_losses=yr[[f"new_{c}" for c in COMPONENTS]].sum().sum(),
                   member_months_lost=yr.member_months_lost.sum(),
                   **{f"off_{c}_dec": yr[f"off_{c}"].iloc[-1] for c in COMPONENTS})
        led.derived(f"mcd_off_coverage_dec_{y}_{sc}", row["off_coverage_dec"], "people",
                    f"people off coverage at end of Dec {y} (cumulative, all components)", inputs_common)
        mm = led.derived(f"mcd_member_months_lost_{y}_{sc}", row["member_months_lost"], "member-months",
                         f"sum over {y} months of people off coverage", inputs_common)
        for k in pmpm:
            row[f"usd_federal_{k}"] = yr[f"usd_federal_{k}"].sum()
            row[f"usd_state_{k}"] = yr[f"usd_state_{k}"].sum()
            led.derived(f"mcd_usd_federal_{k}_{y}_{sc}", row[f"usd_federal_{k}"], "USD",
                        f"mcd_member_months_lost_{y}_{sc} * mcd_pmpm_{k} * mcd_federal_match_aca  [bucket 1]",
                        [f"mcd_member_months_lost_{y}_{sc}", f"mcd_pmpm_{k}", "mcd_federal_match_aca"])
            led.derived(f"mcd_usd_state_{k}_{y}_{sc}", row[f"usd_state_{k}"], "USD",
                        f"mcd_member_months_lost_{y}_{sc} * mcd_pmpm_{k} * (1 - mcd_federal_match_aca)  [bucket 2]",
                        [f"mcd_member_months_lost_{y}_{sc}", f"mcd_pmpm_{k}", "mcd_federal_match_aca"])
            ck.close(f"[{sc}] {y} federal $ = member-months x PMPM x 90%", row[f"usd_federal_{k}"],
                     mm * pmpm[k] * fed, rel_tol=1e-9)
        annual.append(row)

mo = pd.concat(monthly, ignore_index=True)
an = pd.DataFrame(annual)

# ---- gates across scenarios --------------------------------------------------------------------------------------
for y in YEARS:
    a = an[an.year == y].set_index("scenario")
    for col in ["off_coverage_dec", "member_months_lost", "usd_federal_countycare"]:
        ck.ordered(f"{y} {col}: low <= mid <= high", *(a.loc[s, col] for s in SC))
    ck.true(f"{y} new losses sum to change in stock (mid)",
            np.isclose(a.loc["mid", "new_losses"],
                       a.loc["mid", "off_coverage_dec"] - (an[(an.year == y - 1) & (an.scenario == "mid")].off_coverage_dec.sum())))
pre = mo[(mo.month < str(nc_month))]
ck.equal("no losses before the noncitizen cut (Oct 2026)", float(pre.off_coverage.abs().sum()), 0.0)
mid = an[an.scenario == "mid"].set_index("year")
for sc in SC:  # how many work-requirement losses are people already working/earning enough (Urban: workers lose too)
    a = an[(an.scenario == sc) & (an.year == YEARS[-1])].iloc[0]
    ck.true(f"[{sc}] work-req losses <= subject people", a.off_work_req_dec <= n_subj)
    led.derived(f"mcd_work_req_losses_already_compliant_{sc}",
                max(0.0, a.off_work_req_dec - float(led.rows["mcd_subject_noncompliant_people"]["value"])), "people",
                "work-req losses above the number of subject adults not already working/earning enough (lower bound)",
                [f"mcd_work_req_loss_total_{sc}", "mcd_subject_noncompliant_people"])

# triangulation (informational, not pass/fail): Urban Institute for RWJF (Mar 2026), Illinois, 2028.
# Urban reports the decline in AVERAGE MONTHLY 2028 expansion enrollment as % of enrollees; we apply its Illinois %
# to Cook's baseline. Urban covers work requirements + six-month redeterminations only (no noncitizen cut), includes
# new applicants denied, and models re-enrollment. Our method stays ours; Urban is a comparison.
urb = pd.read_csv(PROC / "urban_il_2028.csv").set_index("scenario")
y = YEARS[-1]
tri_rows = []
for sc in SC:
    yr = mo[(mo.scenario == sc) & (mo.month.str.startswith(str(y)))]
    avg = {c: yr[f"off_{c}"].mean() for c in COMPONENTS}
    tri_rows.append(dict(source="ours", scenario=sc, redeterminations=avg["renewal_6mo"],
                         work_requirements=avg["work_req"] + avg["paperwork"] + avg["verification"],
                         noncitizen=avg["noncitizen"]))
for sc, r in urb.iterrows():
    led.observed(f"urban_il_2028_total_pct_{sc}", -r.total_pct / 100, "share", f"Urban/RWJF 2026, {r.source_ref}")
    tri_rows.append(dict(source="urban_x_cook_baseline", scenario=f"{sc} mitigation",
                         redeterminations=-r.redet_pct / 100 * base, work_requirements=-r.work_req_pct / 100 * base,
                         noncitizen=float("nan")))
# HFS's own (internal, draft) work-requirement estimate, as a share of HFS's 700k ACA adults, applied to Cook
for lab, val in (("HFS internal estimate, low end", hfs_lo), ("HFS internal estimate, high end", hfs_hi)):
    tri_rows.append(dict(source="hfs_internal_x_cook_baseline", scenario=lab, redeterminations=float("nan"),
                         work_requirements=val / hfs_den * base, noncitizen=float("nan")))
tri = pd.DataFrame(tri_rows)
tri["total_excl_noncitizen"] = tri.redeterminations.fillna(0) + tri.work_requirements
tri["total_incl_noncitizen"] = tri.total_excl_noncitizen + tri.noncitizen.fillna(0)
tri["pct_of_baseline_excl_noncitizen"] = tri.total_excl_noncitizen / base
tri.insert(2, "measure", f"average monthly people off coverage, {y}, Cook ACA adults")
ours_mid = tri[(tri.source == "ours") & (tri.scenario == "mid")].iloc[0]
for col in ("total_excl_noncitizen", "total_incl_noncitizen"):
    led.derived(f"mcd_avg_off_coverage_{y}_mid_{col.replace('total_', '')}", ours_mid[col], "people",
                f"mean over {y} months of people off coverage (mid), {col}", [f"mcd_member_months_lost_{y}_mid"])
lo, hi = -urb.loc["high", "total_pct"] / 100, -urb.loc["low", "total_pct"] / 100
ck.between(f"ours (mid) within Urban Illinois range {lo:.0%}-{hi:.0%} of enrollees ({y}, excl. noncitizens)",
           ours_mid.pct_of_baseline_excl_noncitizen, lo, hi, soft=True,
           detail="informational: Urban includes denied new applicants and has the full renewal effect all year")

# ---- tracer: month and save ------------------------------------------------------------------------------------
for m in ("2026-10", "2027-04", "2027-12", "2028-12"):
    r = mo[(mo.scenario == "mid") & (mo.month == m)].iloc[0]
    trace(STEP, f"medicaid_month:{m}", "mid: people off coverage", round(r.off_coverage), "cumulative, all components")
flush(STEP)
mo.to_csv(OUT / "tables" / "medicaid_monthly.csv", index=False)
an.to_csv(OUT / "tables" / "medicaid_annual.csv", index=False)
tri.to_csv(OUT / "tables" / "medicaid_triangulation.csv", index=False)

pd.set_option("display.width", 200)
show = an[["scenario", "year", "off_coverage_dec", "member_months_lost", "usd_federal_countycare", "usd_state_countycare"]].copy()
for c in ["usd_federal_countycare", "usd_state_countycare"]:
    show[c] = (show[c] / 1e6).round(1)
print(show.round(0).to_string(index=False))
print(an[["scenario", "year"] + [f"off_{c}_dec" for c in COMPONENTS]].round(0).to_string(index=False))
print(tri.round(3).to_string(index=False))
ck.finish()
led.save()
