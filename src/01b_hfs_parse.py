"""Step 2b: parse HFS Medicaid enrollment (Cook County page + FY2025 enrollment-by-zip PDF).

Outputs data/processed/hfs_cook_enrollment.csv   (category x fiscal year, Cook County)
        data/processed/hfs_zip_fy2025.csv         (every zip in Illinois, 6 categories; '*' = suppressed small count)
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

STEP = "01b_hfs_parse"
ck = Checks(STEP)
P = load_params()
A = P["verification"]["anchors"]


def clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).replace("​", "").strip()


# ---- Cook County page --------------------------------------------------------------
html = (RAW / "hfs/cook_enrollment.html").read_text(encoding="utf-8", errors="replace")
rows, years = [], None
for i, tr in enumerate(re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S | re.I)):
    cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S | re.I)]
    if cells and cells[1].startswith("FY"):
        years = [c for c in cells[1:] if c]
        continue
    for fy, v in zip(years, cells[1:]):
        rows.append(dict(category=cells[0], fiscal_year=fy, enrollees=int(v.replace(",", "")),
                         source_ref=f"hfs/cook_enrollment.html table row {i}"))
cook = pd.DataFrame(rows)
cook.to_csv(PROC / "hfs_cook_enrollment.csv", index=False)

fy25 = cook[cook.fiscal_year == "FY2025"].set_index("category").enrollees
ck.equal("anchor: Cook ACA FY2025", int(fy25["ACA"]), A["hfs_cook_aca_fy2025"])
ck.equal("anchor: Cook total FY2025", int(fy25["Total"]), A["hfs_cook_total_fy2025"])
for fy, g in cook.groupby("fiscal_year"):
    s = g.set_index("category").enrollees
    parts = s.drop("Total").sum()
    ck.sums_to(f"{fy}: categories sum to Total", parts, s["Total"])

# ---- Enrollment by zip PDF -----------------------------------------------------------
COLS = ["children", "adults_disabled", "aca_adults", "other_adults", "seniors", "partial"]
TOKEN = r"(\d+|\*)"
line_re = re.compile(r"^(\d{5}) " + " ".join([TOKEN] * 6) + r"$")
zrows, odd = [], []
with pdfplumber.open(RAW / "hfs/fy25_enrollment_by_zip.pdf") as pdf:
    header = (pdf.pages[0].extract_text() or "")
    ck.true("zip PDF header: SFY 2025", "SFY 2025" in header)
    ck.true("zip PDF header: column order Children, disabilities, ACA, Other, Seniors, Partial",
            re.search(r"Children.*disabilities.*Adults.*Adults.*Seniors.*Partial", header.replace("\n", " ")) is not None)
    for pg_no, page in enumerate(pdf.pages, 1):
        for line in (page.extract_text() or "").splitlines():
            line = line.strip()
            m = line_re.match(line)
            if m:
                vals = m.groups()
                zrows.append(dict(zip=vals[0], **{c: v for c, v in zip(COLS, vals[1:])},
                                  source_ref=f"hfs/fy25_enrollment_by_zip.pdf page {pg_no}"))
            elif re.match(r"^\d{5}\b", line):
                odd.append((pg_no, line))
z = pd.DataFrame(zrows)
ck.equal("zip PDF: no unparsed zip lines", len(odd), 0, detail=f"examples: {odd[:5]}")
ck.unique("zip PDF: one row per zip", z, ["zip"])
ck.between("zip PDF: Illinois zip count (USPS ~1,590 incl. PO-box zips)", len(z), 1400, 1700)
ck.true("zip PDF: all zips are Illinois (600xx-629xx)", z.zip.str[:2].isin(["60", "61", "62"]).all())

for c in COLS:
    z[c + "_suppressed"] = z[c].eq("*")
    z[c] = pd.to_numeric(z[c].replace("*", None))
sup = z.aca_adults_suppressed.sum()
ck.true("suppressed ('*') ACA cells are a small share of zips", sup / len(z) < 0.15, detail=f"{sup} zips suppressed", soft=True)
z.to_csv(PROC / "hfs_zip_fy2025.csv", index=False)

# Rough state check (exact Cook check needs the ZCTA-county file; done in step 2e)
ck.between("zip PDF: statewide ACA adults (sum of zips) plausible 700k-1.1M",
           z.aca_adults.sum(), 700_000, 1_100_000)

for zz in tracers()["zips"]:
    r = z[z.zip == zz]
    if ck.true(f"tracer zip {zz} present in HFS zip file", len(r) == 1):
        r = r.iloc[0]
        trace(STEP, f"zip:{zz}", "HFS ACA adults FY2025", int(r.aca_adults), r.source_ref)
        trace(STEP, f"zip:{zz}", "HFS total comprehensive FY2025",
              int(r[["children", "adults_disabled", "aca_adults", "other_adults", "seniors"]].sum()), r.source_ref)
flush(STEP)

print(fy25.to_string())
ck.finish()
