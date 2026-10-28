"""Step 2e: automated spot checks. Re-read a random sample of parsed rows from the raw files with a
DIFFERENT method than the parsers used, and require an exact match.

- IDHS office HTML: flatten the page to plain text, search for "code name households persons"
  (the parser walked <tr>/<td> cells instead).
- PDFs (IDHS county, HFS zip): extract text with pdfium (pypdfium2); the parsers used pdfminer (pdfplumber).
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import PROC, RAW  # noqa: E402

STEP = "01e_independent_recheck"
ck = Checks(STEP)
N = 40
SEED = 2026


def pdf_pages_text(path):
    doc = pdfium.PdfDocument(str(path))
    return {i + 1: doc[i].get_textpage().get_text_range() for i in range(len(doc))}


def fmt(n):
    return f"{int(n):,}"


# ---- IDHS office pages ----------------------------------------------------------------------
off = pd.read_csv(PROC / "snap_offices_monthly.csv", dtype={"code": str})
flat = {}
for r in off.sample(N, random_state=SEED).itertuples():
    f = r.source_ref.split(" table row")[0]
    if f not in flat:
        html = (RAW / f).read_text(encoding="utf-8", errors="replace")
        flat[f] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html).replace("&amp;", "&"))
    name = "" if r.kind == "subtotal" else re.escape(r.office) + " "
    pat = re.escape(r.code) + " " + name + re.escape(fmt(r.households)) + " " + re.escape(fmt(r.persons))
    ck.true(f"IDHS {r.month} {r.code}: {fmt(r.households)} hh / {fmt(r.persons)} persons found in page text",
            re.search(pat, flat[f]) is not None)

# every Cook subtotal (these drive the analysis), not just a sample
cook = pd.read_csv(PROC / "snap_cook_monthly.csv")
for r in cook.itertuples():
    f = r.source_ref.split(" table row")[0]
    text = flat.get(f) or re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", (RAW / f).read_text(encoding="utf-8", errors="replace")))
    ck.true(f"IDHS {r.month} COOK COUNTY {fmt(r.persons)} persons found in page text",
            f"COOK COUNTY {fmt(r.households)} {fmt(r.persons)}" in text)

# ---- IDHS county PDF (all rows) -----------------------------------------------------------------
cty = pd.read_csv(PROC / "snap_county_2025_09.csv")
pages = pdf_pages_text(RAW / "idhs/snap_county_2025_09.pdf")
alltext = re.sub(r"\s+", " ", " ".join(pages.values()))
for r in cty.itertuples():
    ck.true(f"county PDF {r.county} {fmt(r.persons)} (pdfium)", f"{r.county} {fmt(r.persons)}" in alltext)

# ---- HFS zip PDF ----------------------------------------------------------------------------------
z = pd.read_csv(PROC / "hfs_zip_fy2025.csv", dtype={"zip": str})
cols = ["children", "adults_disabled", "aca_adults", "other_adults", "seniors", "partial"]
pages = pdf_pages_text(RAW / "hfs/fy25_enrollment_by_zip.pdf")
cook_frame = set(pd.read_csv(PROC / "zcta_cook.csv", dtype={"zcta": str}).zcta)
sample = pd.concat([z.sample(N, random_state=SEED), z[z.zip.isin(cook_frame)].sample(N, random_state=SEED)])
for r in sample.drop_duplicates("zip").itertuples():
    pg = int(r.source_ref.rsplit(" ", 1)[1])
    vals = ["*" if pd.isna(getattr(r, c)) else str(int(getattr(r, c))) for c in cols]
    line = r.zip + " " + " ".join(vals)
    text = re.sub(r"[ \t]+", " ", pages[pg])
    ck.true(f"HFS zip {r.zip} row matches pdfium text on page {pg}", line in text, detail=line)

ck.finish()
