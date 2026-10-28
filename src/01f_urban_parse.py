"""Parse Illinois rows from the Urban Institute / RWJF report (Buettgens et al., March 2026): projected decline in
average monthly Medicaid expansion enrollment in 2028 from H.R. 1 work requirements + six-month redeterminations.
This is the source of the "400,000 Illinoisans" figure in the CCH FY27 deck (Crain's, Mar 2026: "The Robert Wood
Johnson Foundation has estimated 400,000 Illinoisans could lose coverage by 2028"); 400k ~ the low-mitigation 415k.
Used only for triangulation (step 5). Tables are found by title, not page number.
  Table 3:  total decline, # (thousands) and %, by mitigation scenario (high / medium / low)
  Table A.2: split into six-month redeterminations only, and work requirements on top of that
"""
import re
import sys
from pathlib import Path

import pandas as pd
import pdfplumber

sys.path.insert(0, str(Path(__file__).parent))
from lib.checks import Checks  # noqa: E402
from lib.common import PROC, RAW  # noqa: E402

STEP = "01f_urban_parse"
ck = Checks(STEP)
PDF = RAW / "rwjf/urban_medicaid_work_req_2028.pdf"
SCEN = ["high", "medium", "low"]  # column order in both tables (high mitigation = fewest losses)
NUM = r"(-?[\d,]+)\s+(-?\d+)%"

with pdfplumber.open(PDF) as pdf:
    pages = [(i + 1, p.extract_text() or "") for i, p in enumerate(pdf.pages)]


def il_row(title, n_pairs):
    hits = [(n, t) for n, t in pages if title in t and "Illinois" in t]
    ck.equal(f"one page with '{title}' and an Illinois row", len(hits), 1)
    n, t = hits[0]
    line = next(ln for ln in t.splitlines() if ln.startswith("Illinois "))
    pairs = re.findall(NUM, line)
    ck.equal(f"{title}: Illinois row has {n_pairs} (#, %) pairs", len(pairs), n_pairs, detail=line)
    return n, line, [(float(a.replace(",", "")), float(b)) for a, b in pairs]


p3, l3, t3 = il_row("TABLE 3", 3)
pa, la, a2 = il_row("APPENDIX TABLE A.2", 6)
rows = []
for i, sc in enumerate(SCEN):
    total, pct = t3[i]
    redet, redet_pct = a2[i]
    wr, wr_pct = a2[3 + i]
    rows.append(dict(scenario=sc, total_k=total, total_pct=pct, redet_k=redet, redet_pct=redet_pct, work_req_k=wr,
                     work_req_pct=wr_pct, implied_base_k=total / (pct / 100),
                     source_ref=f"rwjf/urban_medicaid_work_req_2028.pdf p{p3} Table 3; p{pa} Table A.2"))
df = pd.DataFrame(rows)

ck.equal("anchor: Illinois low-mitigation total = -415k (the ~400k cited by CCH)", df.total_k.iloc[2], -415.0)
for r in df.itertuples():
    ck.close(f"[{r.scenario}] Table 3 total = A.2 redeterminations + work requirements (rounding)",
             r.redet_k + r.work_req_k, r.total_k, abs_tol=2)
ck.close("implied 2028 Illinois expansion base consistent across scenarios (within 3%)",
         df.implied_base_k.max(), df.implied_base_k.min(), rel_tol=0.03)
ck.ordered("losses: high mitigation <= medium <= low", *(-df.total_k))
df.to_csv(PROC / "urban_il_2028.csv", index=False)
print(df.round(1).to_string(index=False))
ck.finish()
