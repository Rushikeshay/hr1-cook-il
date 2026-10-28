# H.R. 1 impact on Cook County — Medicaid & SNAP

Estimates how many Cook County, IL residents lose Medicaid or SNAP (or get smaller SNAP benefits) because of H.R. 1, and how many dollars leave the county, 2026–2028. Results by year, program, scenario, and zip code.

- **[PLAN.md](PLAN.md)**: the agreed plan, confirmed facts with sources, and method decisions. Read it first.
- **[params.yaml](params.yaml)**: every number and assumption, each labeled `observed` / `derived` / `assumed` with a source. Change scenarios here, never in code.

## Environment
- Python: conda env **BED** → `C:\Users\rushikeshjadhav\AppData\Local\miniconda3-pbe\envs\BED\python.exe` (not on PATH). On another machine, create an env with pandas, geopandas, pyogrio, matplotlib, pyyaml, requests, pdfplumber, openpyxl, truststore (conda-forge).
- Python HTTPS fails certificate checks on the work machine (corporate TLS). Scripts call `truststore.inject_into_ssl()`. Don't disable verification.
- Census API needs a free key: `CENSUS_API_KEY=...` in `.env` (gitignored; template in `.env.example`).
- IDHS (dhs.state.il.us) blocks requests without a browser User-Agent; `src/00_fetch.py` sends one.
- `data/raw/` is gitignored (~180 MB). Rebuild with `python src/00_fetch.py`.

## Layout
```
src/NN_*.py        one numbered script per step, run in order
data/raw/          downloads, untouched
data/processed/    cleaned intermediate tables
output/figures/    PNG + the CSV behind each chart
output/tables/
methods.md         plain-language method + limitations (<2 pages)
```

## Rules
- Label every number observed, derived or assumed.
- Don't invent data. If a file or column is missing, stop and ask.
- Three separate dollar buckets: federal $ lost; state $ withdrawn as a direct result of H.R. 1; new state costs (Cook share). Never sum them silently.
- SNAP "observed drop" ≠ H.R. 1 effect: compare to the same months a year earlier and the pre-Feb 2026 trend.
- Medicaid loss rates (19/30/40%) all apply to the same base: adults subject to the work requirement. Paperwork losses among exempt adults and churn from 6-month renewals are separate parameters.

## Status (2026-10-28)
Run everything: `python src/run_all.py` (stops on first failed check). Tests: `python -m pytest tests -q`.
Check results: output/checks/report.md. Tracers: output/trace/trace_report.md. Lineage: `python src/trace.py <id>`.

Done: Step 0 (checks/ledger/tracer/spotcheck helpers + tests), Step 1 (manifest, 219 checks), Step 2 (parse):
- 01a SNAP: IDHS office pages Jan 2024-Sep 2026 (Feb 2024 not published). **Cook is only a subtotal row; no
  Chicago/suburban split exists in IDHS data.** "SPECIALTY OFFICES" subtotal starts Jul 2025 = series break.
  Sept 2025 county PDF (881,937) vs office table (851,244) differ +3.6%: flagged, office series used for trend.
- 01b HFS: Cook page (anchors match) + zip PDF, which HAS an ACA-adult column (use it for zip allocation).
- 01c CCH deck: ACA $700M / 69,768 members -> PMPM $836; charity care + payer mix hand-transcribed from p8 chart
  labels, each verified against the PDF text layer. Column order of p25 verified from the page image.
- 01d geo/ACS: 177 Cook ZCTAs (56 Chicago by area overlap, 21 border, tract-population-weighted Cook share);
  HFS zip ACA Cook portion 358,698 vs county 364,204 (-1.5%); 60 Cook-area PO-box zips have no ZCTA.
  ACS: Cook holds 60% of IL noncitizens, 47% of IL SNAP households.

- 01e: automated spot checks (user does NOT want manual sign-off): re-reads samples with a different method
  (HTML text search; pdfium vs pdfminer), 253 checks.
- Decisions 2026-10-28: no Chicago/suburban SNAP series (zip-level only); SNAP changes scaled to residence basis by
  Sept 2025 county/office ratio (1.036); noncitizen Cook share mid/high = ACS 60%, low = CBS 44%.
- Step 3 `02_snap_series.py`: pre-trend -0.24%/mo (Jan 2024-Jun 2025). H.R. 1 SNAP persons lost by Sep 2026
  (residence basis): low 134k (beyond trend from Feb 2026, legal start), mid 188k (from Dec 2025, when IDHS first
  applied the work requirement; IM 01/15/2026 + CN 26.01), high 218k (all, flat counterfactual). Headline = mid.
  Triangulation: IDHS ~148k statewide work-requirement losses by ~Jun 2026 x Cook ~45% = ~67k vs our May-Jun
  excess 62k. "Shutdown processing errors / accelerated recert" explanations are unverified (not used).

- Step 4 `03_pums_shares.py` (rules in `src/lib/pums_rules.py`, 26 synthetic tests in tests/test_pums_rules.py).
  PUMS re-cut now has 80 replicate weights, ADJINC, and the housing file (FS = SNAP receipt is household-level).
  Anchors pass: weighted pop vs B01003, Medicaid 19-64 vs C27007, SNAP households vs B22003.
  Decisions 2026-10-28: half-time students count as COMPLIANT (HFS), overriding PLAN item 2; headline universe
  is BROAD (no poverty cap, caretaker child rule) = 298k weighted = 82% of HFS 364k. PUMS supplies SHARES only;
  people counts always start from HFS 364,204. Plan's narrow universe (25% of HFS) kept as 'plan_universe'.
  Headline: share (a) 0.481 (SE 0.007), (b) either 0.212. Exempt: disability, caregiver-of-disabled proxy,
  SNAP/TANF. SNAP: time-limited 12.7% of PUMS SNAP persons (980k), not meeting 80 hrs 4.9%; SNAP households
  with no 60+/disabled member 41%.
- Step 5 `04_medicaid.py`: monthly 2026-2028 by component (noncitizen Oct 2026; work req from Apr 2027, first
  renewals spread Mar 2027-Feb 2028; paperwork; 6-month renewals Oct 2027-Sep 2028; 2028 verification).
  No re-enrollment except as built into Urban's renewal rate. Noncitizens ARE in our totals (they show the policy).
  Decision 2026-10-28: 6-month renewal losses = Urban/RWJF Illinois redetermination-only rates (8/15/15%,
  params six_month_renewal_loss), replacing the unsourced 0/2/4% placeholder; applied to people still enrolled.
  Off coverage Dec 2028: low 62k / mid 113k / high 141k. Federal $ (CountyCare PMPM $836): 2027 mid $230M,
  2028 mid $888M; state 10% separate. HFS PMPM still missing (dollars use CountyCare only).
  Urban/RWJF (Mar 2026) is the source of CCH's "400k" (= Illinois low mitigation 415k; parsed in 01f). 2028 avg
  monthly, Cook, excl. noncitizens: ours mid 93k (25%) vs Urban 95k/160k/208k (26/44/57%). Ours is lower mainly
  because Urban also counts denied new applicants and has the full renewal effect all of 2028.
  User rule: keep our method; use Urban to correct weak spots and as a cited comparison.

Next: Step 6 `05_snap.py`.

## Open questions
- Medicaid model has no re-enrollment (people who lose coverage stay off), so later-year counts lean high
- Not modeled: new applicants denied by the work requirement (Urban includes them)
- No cited source yet for the 19/30/40% loss rates
- Share of Cook SNAP households affected by the LIHEAP/utility-allowance change
- HFS statewide ACA cost per member
- The 2028 verification parameter is a placeholder
