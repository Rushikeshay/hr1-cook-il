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

Gate pending: user spot-check sign-off in output/checks/spot_checks.md.
Next: Step 3 `02_snap_series.py` (counterfactual vs same months prior year / pre-Feb 2026 trend; handle Jul 2025 break),
then Step 4 `03_pums_shares.py` + tests/test_pums_rules.py.

## Open questions
- No cited source yet for the 19/30/40% loss rates
- Share of Cook SNAP households affected by the LIHEAP/utility-allowance change
- HFS statewide ACA cost per member
- The extra-churn and 2028 verification parameters are placeholders
