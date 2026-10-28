"""Step 2a: parse IDHS SNAP sources into tidy tables.

Inputs  data/raw/idhs/offices/snap_offices_YYYY_MM.html   (monthly, households + persons by office)
        data/raw/idhs/snap_county_2025_09.pdf            (persons by county, Sept 2025)
Outputs data/processed/snap_offices_monthly.csv           (every row of every month, incl. subtotal rows)
        data/processed/snap_cook_monthly.csv              (Cook subtotal by month)
        data/processed/snap_county_2025_09.csv

Note: the office pages list downstate offices individually but Cook only as one subtotal row,
so a Chicago vs. suburban split is NOT available from IDHS.
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import PROC, RAW, load_params  # noqa: E402
from lib.tracer import flush, trace, tracers  # noqa: E402

STEP = "01a_snap_parse"
ck = Checks(STEP)
P = load_params()
SUBTOTALS = {"DOWNSTATE", "COOK COUNTY", "SPECIALTY OFFICES", "TOTAL STATE"}


def num(s):
    return int(s.replace(",", "")) if s else None


def parse_office_page(path):
    html = path.read_text(encoding="utf-8", errors="replace")
    month = pd.Period(path.stem.replace("snap_offices_", "").replace("_", "-"), "M")
    out = []
    for i, row in enumerate(re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)):
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", c)).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S | re.I)]
        if len(cells) != 4 or cells[0] == "Office Number":
            continue  # header rows and the 3-column "consolidated offices" table
        code, name, hh, persons = cells
        kind = "subtotal" if code.upper() in SUBTOTALS else "office"
        out.append(dict(month=str(month), kind=kind, code=code.upper() if kind == "subtotal" else code,
                        office=name if kind == "office" else code.upper(),
                        households=num(hh), persons=num(persons),
                        source_ref=f"{path.relative_to(RAW).as_posix()} table row {i}"))
    return out


# ---- monthly office pages -----------------------------------------------------
rows = []
for p in sorted((RAW / "idhs/offices").glob("snap_offices_*.html")):
    rows += parse_office_page(p)
df = pd.DataFrame(rows)

ck.no_nulls("office table: no missing values", df, ["month", "code", "households", "persons"])
ck.unique("office table: one row per month x code", df, ["month", "code"])
ck.true("persons >= households on every row", (df.persons >= df.households).all())
ck.months_contiguous("office months contiguous", df.month, soft=True)  # Feb 2024 is not published

# IDHS added a "SPECIALTY OFFICES" subtotal in July 2025. Before that, specialty cases sat inside
# Cook/downstate, so July 2025 is a series break (cases reclassified, not people leaving SNAP).
SPECIALTY_START = "2025-07"
for m, g in df.groupby("month"):
    sub = g[g.kind == "subtotal"].set_index("code")
    expected = SUBTOTALS if m >= SPECIALTY_START else SUBTOTALS - {"SPECIALTY OFFICES"}
    ck.equal(f"{m}: expected subtotal rows present", sorted(sub.index), sorted(expected))
    offices = g[g.kind == "office"]
    for col in ("households", "persons"):
        ck.sums_to(f"{m}: sum of downstate offices = DOWNSTATE ({col})", offices[col].sum(), sub.loc["DOWNSTATE", col])
        parts = [c for c in ("DOWNSTATE", "COOK COUNTY", "SPECIALTY OFFICES") if c in sub.index]
        ck.sums_to(f"{m}: {' + '.join(parts)} = TOTAL ({col})", sub.loc[parts, col].sum(), sub.loc["TOTAL STATE", col])

A = P["verification"]["anchors"]
june = df[(df.month == "2026-06") & (df.code == "COOK COUNTY")].iloc[0]
ck.equal("anchor: Cook households June 2026", int(june.households), A["idhs_cook_households_2026_06"])
ck.equal("anchor: Cook persons June 2026", int(june.persons), A["idhs_cook_persons_2026_06"])

cook = (df[df.code == "COOK COUNTY"][["month", "households", "persons", "source_ref"]]
        .sort_values("month").reset_index(drop=True))
state = df[df.code == "TOTAL STATE"].set_index("month")
cook["state_persons"] = cook.month.map(state.persons)
cook["cook_share_persons"] = cook.persons / cook.state_persons
cook["series_break"] = cook.month.eq(SPECIALTY_START)
cook["note"] = cook.series_break.map({True: "IDHS starts reporting SPECIALTY OFFICES separately; "
                                            "part of the change is reclassification", False: ""})
ck.between("Cook share of state persons stays 40-55% every month",
           cook.cook_share_persons.min(), 0.40, 0.55)
mom = cook.persons.pct_change().abs()
ck.between("largest month-to-month Cook change < 10% (bigger suggests a parse error)", mom.max(), 0, 0.10)
ck.true("Cook persons never rise more than 2% in a month", (cook.persons.pct_change().fillna(0) < 0.02).all(), soft=True)

# ---- Sept 2025 county PDF ------------------------------------------------------
pdf_path = RAW / "idhs/snap_county_2025_09.pdf"
crow = []
with pdfplumber.open(pdf_path) as pdf:
    for pg_no, page in enumerate(pdf.pages, 1):
        for line in (page.extract_text() or "").splitlines():
            m = re.fullmatch(r"(.+?) ([\d,]+)", line.strip())
            if m and m.group(1) != "Counties Snap Individuals":
                crow.append(dict(county=m.group(1), persons=num(m.group(2)),
                                 source_ref=f"idhs/snap_county_2025_09.pdf page {pg_no}"))
county = pd.DataFrame(crow)
total = county[county.county == "Total"].persons.iloc[0]
county = county[county.county != "Total"]
ck.equal("county PDF: 102 Illinois counties", len(county), 102)
ck.sums_to("county PDF: counties sum to printed Total", county.persons.sum(), total)

# ---- reconcile the two IDHS sources (flag, don't force) -------------------------
sep_cook_office = int(cook.loc[cook.month == "2025-09", "persons"].iloc[0])
sep_cook_county = int(county.loc[county.county == "Cook", "persons"].iloc[0])
sep_state_office = int(state.loc["2025-09", "persons"])
gap = sep_cook_county / sep_cook_office - 1
ck.close("Sept 2025 Cook: county PDF vs office table (within 1%)", sep_cook_county, sep_cook_office,
         rel_tol=0.01, soft=True,
         detail=f"county PDF {sep_cook_county:,} vs office {sep_cook_office:,} ({gap:+.1%}); "
                f"state {total:,} vs {sep_state_office:,} ({total / sep_state_office - 1:+.1%}). "
                "Different definitions (likely county of residence vs. servicing office, or a different "
                "count date). The office series is used for the time trend; the gap is reported.")

# ---- save, tracers, spot checks ------------------------------------------------
df.to_csv(PROC / "snap_offices_monthly.csv", index=False)
cook.to_csv(PROC / "snap_cook_monthly.csv", index=False)
county.to_csv(PROC / "snap_county_2025_09.csv", index=False)

tm = tracers()["month"]
r = cook[cook.month == tm].iloc[0]
trace(STEP, f"month:{tm}", "Cook SNAP persons (IDHS office table)", int(r.persons), r.source_ref)
trace(STEP, f"month:{tm}", "Cook SNAP households (IDHS office table)", int(r.households), r.source_ref)
flush(STEP)

print(cook[["month", "households", "persons"]].tail(14).to_string(index=False))
ck.finish()
