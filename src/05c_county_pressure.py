"""Step 6c: pressure on county resources. Public figures only; nothing here reflects internal county decisions.

1. CountyCare (Cook County Health's Medicaid plan): CountyCare ACA members likely to lose coverage and the CountyCare
   payments (capitation) that leave with them, by Cook fiscal year (Dec-Nov) and scenario.
     CountyCare share of Cook ACA adults = CCH FY27 budgeted ACA members / HFS Cook ACA adults (assumed: same loss rate)
     capitation lost = CountyCare member-months lost x CountyCare ACA PMPM (CCH deck)
   Compared with the County's own FY2027 forecast (Health Fund revenue -$486.5M from lower CountyCare membership;
   $138.0M OBBBA fallout for the hospital system; $214.7M Health Fund gap) and CCH charity care history.
2. Local spending: SNAP dollars lost x USDA ERS multiplier (1.54 GDP per $1; 13,560 jobs per $1B), illustrative.
These are pressures, not forecasts of county decisions. Kept separate from the three dollar buckets.
"""
import html
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import OUT, PROC, RAW, load_params  # noqa: E402
from lib.ledger import Ledger, load  # noqa: E402

STEP = "05c_county_pressure"
ck = Checks(STEP)
led = Ledger(STEP)
P = load_params()
C = P["county"]
SC = P["meta"]["scenarios"]
YEARS = P["meta"]["analysis_years"]
L = load().set_index("id")
v = lambda i: float(L.loc[i, "value"])  # noqa: E731


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip()


rel_txt = (RAW / "cook/fy2027_preliminary_budget_forecast_release.html").read_text(encoding="utf-8", errors="replace")
rel_txt = norm(html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", "", rel_txt, flags=re.S))))
with pdfplumber.open(RAW / "evidence/usda_ers_err265_snap_multiplier_2019.pdf") as pdf:
    ers_txt = norm(" ".join((pg.extract_text() or "") for pg in pdf.pages[:8]))

F = C["fy2027_forecast"]
for k in ("health_fund_gap", "health_revenue_decline", "obbba_hospital_fallout"):
    ck.true(f"County FY2027 forecast quote found: {k}", norm(F[k]["quote"]) in rel_txt)
    led.observed(f"county_fy2027_{k}", F[k]["value"], "USD", f"Cook County FY2027 preliminary forecast release: \"{F[k]['quote']}\"")
ck.true("ERS multiplier quote found in ERR-265", norm(C["snap_multiplier"]["gdp_per_dollar"]["quote"]) in ers_txt)
mult = led.observed("ers_snap_gdp_multiplier", C["snap_multiplier"]["gdp_per_dollar"]["value"], "USD GDP per USD SNAP",
                    "USDA ERS ERR-265 (Canning & Stacy 2019)")
jobs_b = led.observed("ers_snap_jobs_per_billion", C["snap_multiplier"]["jobs_per_billion"]["value"], "jobs per $1B SNAP",
                      "USDA ERS ERR-265 (Canning & Stacy 2019)")

# ---- CountyCare -------------------------------------------------------------------------------------------------------
cc_share = led.derived("countycare_share_of_cook_aca", v("cch_aca_members_2027") / v("mcd_baseline_aca_adults"), "share",
                       "cch_aca_members_2027 / mcd_baseline_aca_adults (CCH FY27 budget members vs HFS June 2025)",
                       ["cch_aca_members_2027", "mcd_baseline_aca_adults"])
ck.between("CountyCare share of Cook ACA adults plausible (10-40%)", cc_share, 0.10, 0.40)
pmpm = v("mcd_pmpm_countycare")
mo = pd.read_csv(OUT / "tables" / "medicaid_monthly.csv")
mo["period"] = pd.PeriodIndex(mo.month, freq="M")
fy_start = int(C["fiscal_year_start_month"]["value"])
mo["county_fy"] = mo.period.dt.year + (mo.period.dt.month >= fy_start).astype(int)
mo["cc_members_off"] = mo.off_coverage * cc_share
mo["cc_capitation_lost"] = mo.cc_members_off * pmpm
rows = []
for sc in SC:
    m = mo[mo.scenario == sc]
    for fy in sorted(m.county_fy.unique()):
        g = m[m.county_fy == fy]
        full = len(g) == 12
        rows.append(dict(scenario=sc, county_fy=fy, months_in_window=len(g), complete_fy=full,
                         cc_members_off_end=g.cc_members_off.iloc[-1], cc_member_months_lost=g.cc_members_off.sum(),
                         cc_capitation_lost_usd=g.cc_capitation_lost.sum()))
        if full:
            led.derived(f"countycare_capitation_lost_fy{fy}_{sc}", g.cc_capitation_lost.sum(), "USD",
                        f"sum over Cook FY{fy} (Dec-Nov) of people off Medicaid x countycare_share_of_cook_aca x mcd_pmpm_countycare",
                        ["countycare_share_of_cook_aca", "mcd_pmpm_countycare", f"mcd_member_months_lost_{fy}_{sc}"])
            led.derived(f"countycare_members_off_end_fy{fy}_{sc}", g.cc_members_off.iloc[-1], "people",
                        f"CountyCare ACA members off coverage at end of Cook FY{fy} (Nov)",
                        ["countycare_share_of_cook_aca", f"mcd_off_coverage_dec_{fy}_{sc}"])
cc = pd.DataFrame(rows)
for fy in (2027, 2028):
    a = cc[cc.county_fy == fy].set_index("scenario")
    ck.ordered(f"FY{fy} CountyCare capitation lost: low <= mid <= high", *(a.loc[s, "cc_capitation_lost_usd"] for s in SC))
ck.true("CountyCare members off never exceed CountyCare ACA members", (mo.cc_members_off <= v("cch_aca_members_2027")).all())

# compare with the County's FY2027 forecast (different measures; shown side by side, not reconciled)
fy27 = cc[cc.county_fy == 2027].set_index("scenario")
cmp = pd.DataFrame([
    dict(measure=f"Our CountyCare ACA capitation lost, Cook FY2027 ({s})", usd=fy27.loc[s, "cc_capitation_lost_usd"],
         source="this analysis (H.R. 1 work requirement, renewals, noncitizens; ACA adults only)") for s in SC] + [
    dict(measure="County forecast: Health Fund revenue decline, FY2027", usd=F["health_revenue_decline"]["value"],
         source="Cook County FY2027 preliminary forecast (all CountyCare programs; federal cuts + Medicare eligibility)"),
    dict(measure="County forecast: OBBBA fallout for the hospital system, FY2027", usd=F["obbba_hospital_fallout"]["value"],
         source="Cook County FY2027 preliminary forecast (CCH patient revenue)"),
    dict(measure="County forecast: Health Fund budget gap, FY2027", usd=F["health_fund_gap"]["value"],
         source="Cook County FY2027 preliminary forecast"),
])
charity = pd.read_csv(PROC / "cch_charity_care.csv")

# ---- local spending from SNAP dollars lost ---------------------------------------------------------------------------
snp = pd.read_csv(OUT / "tables" / "snap_annual.csv")
loc_rows = []
for r in snp[snp.year.isin(YEARS)].itertuples():
    gdp = r.federal_benefits_lost_usd * mult
    jobs = r.federal_benefits_lost_usd / 1e9 * jobs_b
    loc_rows.append(dict(scenario=r.scenario, year=r.year, snap_federal_lost_usd=r.federal_benefits_lost_usd,
                         economic_activity_lost_usd=gdp, jobs_supported_lost=jobs))
    for k, val, unit in (("activity", gdp, "USD"), ("jobs", jobs, "jobs")):
        led.derived(f"snap_local_{k}_lost_{r.year}_{r.scenario}", val, unit,
                    f"snap_usd_federal_benefits_{r.year}_{r.scenario} x ERS {'GDP multiplier' if k == 'activity' else 'jobs per $1B'} (national, illustrative)",
                    [f"snap_usd_federal_benefits_{r.year}_{r.scenario}", "ers_snap_gdp_multiplier" if k == "activity" else "ers_snap_jobs_per_billion"])
loc = pd.DataFrame(loc_rows)

cc.to_csv(OUT / "tables" / "countycare_pressure.csv", index=False)
cmp.to_csv(OUT / "tables" / "county_forecast_comparison.csv", index=False)
charity.to_csv(OUT / "tables" / "cch_charity_care_history.csv", index=False)
loc.to_csv(OUT / "tables" / "snap_local_economy.csv", index=False)
pd.set_option("display.width", 200)
show = cc[cc.complete_fy].copy()
show["cc_capitation_lost_musd"] = (show.cc_capitation_lost_usd / 1e6).round(1)
print(f"CountyCare share of Cook ACA adults: {cc_share:.1%}")
print(show[["scenario", "county_fy", "cc_members_off_end", "cc_capitation_lost_musd"]].round(0).to_string(index=False))
print(cmp.assign(musd=(cmp.usd / 1e6).round(1))[["measure", "musd"]].to_string(index=False))
print(loc.assign(**{c: (loc[c] / 1e6).round(0) for c in ("snap_federal_lost_usd", "economic_activity_lost_usd")}).round(0).to_string(index=False))
ck.finish()
led.save()
