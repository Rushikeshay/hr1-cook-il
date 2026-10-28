"""Step 1 gate: fingerprint every raw file and check it is the kind of file we think it is.

Writes data/raw/MANIFEST.csv (path, source, bytes, sha256, detected type, modified).
On a rerun, a changed hash is flagged: the source was re-published or re-downloaded, so look before trusting it.
"""
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import RAW  # noqa: E402

MANIFEST = RAW / "MANIFEST.csv"
ck = Checks("00b_manifest")


def sniff(path):
    head = path.open("rb").read(2048)
    if head.startswith(b"%PDF"):
        return "pdf"
    if head.startswith(b"PK"):
        return "zip"
    low = head.lower()
    if b"<html" in low or b"<!doctype html" in low:
        return "html"
    try:
        head.decode("utf-8")
        return "text"
    except UnicodeDecodeError:
        return "binary"


EXPECTED_TYPE = {".pdf": "pdf", ".zip": "zip", ".html": "html", ".csv": "text", ".txt": "text"}

sources = json.loads((RAW / "_sources.json").read_text())
rows = []
for rel, url in sorted(sources.items()):
    p = RAW / rel
    if not ck.true(f"present: {rel}", p.exists()):
        continue
    data = p.read_bytes()
    kind = sniff(p)
    rows.append(dict(path=rel, source=url, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                     type=kind, modified=datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="seconds")))
    min_bytes = 200 if p.suffix in (".csv", ".txt") else 1024  # small API extracts (one county row) are fine
    ck.true(f"non-empty (>{min_bytes} B): {rel}", len(data) > min_bytes, detail=f"{len(data)} bytes")
    ck.equal(f"type matches extension: {rel}", kind, EXPECTED_TYPE.get(p.suffix, kind),
             detail="an HTML error page saved as .pdf/.zip would fail here")

# Content checks that catch "downloaded the wrong thing / an error page"
for p in sorted((RAW / "idhs/offices").glob("*.html")):
    t = p.read_text(encoding="utf-8", errors="replace")
    ym = p.stem.replace("snap_offices_", "").replace("_", "-")
    month_name = pd.Period(ym, "M").strftime("%B %Y")
    ck.true(f"IDHS page title matches file month: {p.name}", f"{month_name} - SNAP Data by Servicing Office" in t)
    ck.true(f"IDHS page has COOK COUNTY subtotal: {p.name}", "COOK COUNTY" in t.upper())

hfs = (RAW / "hfs/cook_enrollment.html").read_text(encoding="utf-8", errors="replace")
ck.true("HFS Cook page mentions ACA", "ACA" in hfs)

zcta = pd.read_csv(RAW / "acs/acs5_2024_zcta.csv", dtype={"zcta": str})
ck.between("ACS ZCTA row count (~33.8k US ZCTAs)", len(zcta), 33000, 34500)
ck.true("ACS ZCTA has Cook-area ZCTA 60623", "60623" in set(zcta.zcta))

pums = pd.read_csv(RAW / "pums/pums_2024_5yr_cook.csv", dtype=str, usecols=["SERIALNO", "PUMA"])
ck.between("PUMS Cook persons (5-yr sample ~190-210k)", len(pums), 150_000, 260_000)
ck.equal("PUMS Cook PUMA count", pums.PUMA.nunique(), 36)
pums_h = pd.read_csv(RAW / "pums/pums_2024_5yr_housing_cook.csv", dtype=str, usecols=["SERIALNO", "PUMA"])
ck.between("PUMS Cook housing records (5-yr sample ~85-100k)", len(pums_h), 70_000, 120_000)
ck.equal("PUMS Cook housing PUMA count", pums_h.PUMA.nunique(), 36)
ck.true("every PUMS person has a housing record", pums.SERIALNO.isin(set(pums_h.SERIALNO)).all())

# Compare with the previous manifest
new = pd.DataFrame(rows)
if MANIFEST.exists():
    old = pd.read_csv(MANIFEST).set_index("path")
    for r in new.itertuples():
        if r.path in old.index and old.loc[r.path, "sha256"] != r.sha256:
            ck.true(f"unchanged since last manifest: {r.path}", False, soft=True,
                    detail="file content changed; previous manifest kept as MANIFEST.prev.csv")
    shutil.copy(MANIFEST, RAW / "MANIFEST.prev.csv")
new.to_csv(MANIFEST, index=False)
print(f"manifest: {len(new)} files -> {MANIFEST}")
ck.finish()
