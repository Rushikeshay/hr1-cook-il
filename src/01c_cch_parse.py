"""Step 2c: Cook County Health FY2027 preliminary budget deck.

- Page 25 table (CountyCare 2027 membership and capitation by program): parsed from PDF text.
- Page 8 charts (charity care 2018-2027, payer mix 2019-2027): values are chart data labels,
  transcribed by hand below. Each transcribed number is verified to appear in the page's
  text layer, and payer-mix columns must sum to ~100%.
- Page 7 statewide impact statements are kept for the triangulation table.

Outputs data/processed/cch_countycare_2027.csv, cch_charity_care.csv, cch_payer_mix.csv, cch_statements.csv
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import PROC, RAW  # noqa: E402

STEP = "01c_cch_parse"
ck = Checks(STEP)
PDF = RAW / "cch/prelim_fy27_cch_budget.pdf"
REF = "cch/prelim_fy27_cch_budget.pdf"

with pdfplumber.open(PDF) as pdf:
    text = {i: (pdf.pages[i - 1].extract_text() or "") for i in (7, 8, 24, 25, 26)}

# ---- page 25: CountyCare financial summary --------------------------------------------
# Column order verified against the rendered page image (the text layer splits the 2-line headers).
PROGRAMS = ["ACA Adult", "FHP", "SPD", "MLTSS/LTSS/IMD", "SNC", "HBIS/IC", "TOTAL"]
t25 = text[25]


def row(label):
    line = next(l for l in t25.splitlines() if l.startswith(label))
    vals = re.findall(r"\(?\$?[\d,.]+\)?", line[len(label):])
    return [float(v.strip("()$").replace(",", "")) * (-1 if v.startswith("(") else 1) for v in vals]


members = row("Projected 2027 Membership")
capitation = row("CountyCare Capitation Revenue")
ck.equal("p25: 7 membership values (6 programs + total)", len(members), 7)
ck.equal("p25: 7 capitation values", len(capitation), 7)
ck.sums_to("p25: program members sum to TOTAL", sum(members[:6]), members[6], abs_tol=1)
ck.sums_to("p25: program capitation sums to TOTAL ($M, rounded)", sum(capitation[:6]), capitation[6], abs_tol=3)
# Column order in the PDF header is ACA Adult, FHP, SPD, SNC, HBIS/IC, MLTSS/LTSS/IMD, TOTAL
cc = pd.DataFrame(dict(program=PROGRAMS, members_2027=members, capitation_musd_2027=capitation))
cc["pmpm_usd"] = cc.capitation_musd_2027 * 1e6 / cc.members_2027 / 12
cc["source_ref"] = f"{REF} page 25"
aca = cc.set_index("program").loc["ACA Adult"]
ck.equal("anchor: CountyCare ACA members 2027 = 69,768", int(aca.members_2027), 69768)
ck.equal("anchor: CountyCare ACA capitation = $700M", aca.capitation_musd_2027, 700.0)
ck.between("ACA PMPM plausible ($500-$1,200)", aca.pmpm_usd, 500, 1200)
pm = cc.set_index("program").pmpm_usd
ck.equal("column-order sanity: long-term care (MLTSS) has the highest PMPM", pm.drop("TOTAL").idxmax(), "MLTSS/LTSS/IMD")
ck.equal("column-order sanity: FHP (families/children) has the lowest PMPM", pm.drop("TOTAL").idxmin(), "FHP")
ck.true("p24: avg monthly membership 328,915 stated", "328,915" in text[24])
cc.to_csv(PROC / "cch_countycare_2027.csv", index=False)

# ---- page 8: charts (hand-transcribed data labels) -------------------------------------------
charity = {2018: 398, 2019: 372, 2020: 249, 2021: 230, 2022: 134, 2023: 156,
           2024: 237, 2025: 310, 2026: 385, 2027: 485}
estimated = {2026, 2027}
payer = {  # percent of CCH patients, 2019-2027 (2027 estimated)
    "Medicaid":      [50.8, 56.2, 56.5, 59.7, 61.4, 56.2, 52.8, 48.9, 43.5],
    "Uncompensated": [27.5, 22.6, 21.3, 16.3, 13.1, 18.3, 21.5, 24.8, 30.0],
    "Medicare":      [15.8, 15.7, 15.7, 17.3, 18.1, 17.5, 17.9, 17.3, 17.5],
    "Commercial":    [5.8, 5.6, 6.5, 6.8, 7.4, 8.0, 8.6, 8.9, 9.0],
}
years = list(range(2019, 2028))

t8 = text[8]
tokens = set(re.findall(r"\d+(?:\.\d+)?", t8.replace("$", "")))
for y, v in charity.items():
    ck.true(f"p8 charity {y}: ${v}M appears in page text", str(v) in tokens)
for k, vals in payer.items():
    for y, v in zip(years, vals):
        s = f"{v:g}"
        ck.true(f"p8 payer mix {k} {y}: {s}% appears in page text", s in tokens)
for i, y in enumerate(years):
    total = sum(payer[k][i] for k in payer)
    ck.between(f"p8 payer mix {y} sums to ~100%", total, 99.0, 101.0)

pd.DataFrame([dict(year=y, charity_care_musd=v, estimated=y in estimated,
                   source_ref=f"{REF} page 8 (chart labels; IDPH profiles)") for y, v in charity.items()]
             ).to_csv(PROC / "cch_charity_care.csv", index=False)
pd.DataFrame([dict(year=y, payer=k, pct=v, estimated=y == 2027, source_ref=f"{REF} page 8 (chart labels)")
              for k, vals in payer.items() for y, v in zip(years, vals)]).to_csv(PROC / "cch_payer_mix.csv", index=False)

# ---- page 7 and 26: statements used for triangulation ---------------------------------------
statements = [
    ("Statewide Medicaid losses from work requirements + 6-month renewals (CCH estimate)", 400000, "people", 7, "400,000"),
    ("Statewide noncitizen Medicaid losses Oct 2026 (CCH estimate)", 10000, "people", 7, "10,000"),
    ("Statewide marketplace coverage dropped Jan 2026 (not H.R. 1: ACA tax credits)", 92000, "people", 7, "92,000"),
    ("CCH FY2027 patient revenue impact", -138, "USD millions", 7, "$138M"),
    ("CCH FY2027 added charity care costs", 100, "USD millions", 7, "$100M"),
    ("Cook County Medicaid enrollment decline Sept 2023 - June 2026", -0.23, "share", 26, "23%"),
    ("CountyCare share of Cook Medicaid market", 0.353, "share", 26, "35.3%"),
]
rows = []
for label, val, unit, pg, quote in statements:
    ck.true(f"p{pg} statement present: {quote}", quote in text[pg].replace("\n", " "))
    rows.append(dict(statement=label, value=val, unit=unit, quote=quote, source_ref=f"{REF} page {pg}"))
pd.DataFrame(rows).to_csv(PROC / "cch_statements.csv", index=False)

print(cc[["program", "members_2027", "capitation_musd_2027", "pmpm_usd"]].to_string(index=False))
ck.finish()
