# H.R. 1 impact on Cook County — Medicaid & SNAP

Estimates how many Cook County, IL residents lose Medicaid or SNAP (or get smaller SNAP benefits) because of H.R. 1, and how many dollars leave the county, 2026–2028. Results by year, program, scenario, and zip code.

- **[PLAN.md](PLAN.md)**: the agreed plan, confirmed facts with sources, and method decisions. Read it first.
- **[params.yaml](params.yaml)**: every number and assumption, each labeled `observed` / `derived` / `assumed` with a source. Change scenarios here, never in code.

## Environment
- Python: conda env **BED** → `C:\Users\rushikeshjadhav\AppData\Local\miniconda3-pbe\envs\BED\python.exe` (not on PATH). On another machine, create an env with pandas, geopandas, pyogrio, matplotlib, pyyaml, requests, pdfplumber, openpyxl, truststore (conda-forge).
- Python HTTPS fails certificate checks on the work machine (corporate TLS). Scripts call `truststore.inject_into_ssl()`. Don't disable verification.
- Census API needs a free key in `census_api_key.txt` (project root, gitignored) or env var `CENSUS_API_KEY`.
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

## Status (2026-10-27)
Done:
- Plan and fact check (PLAN.md)
- params.yaml
- `src/00_fetch.py`, which downloads HFS, CCH, IDHS SNAP monthly by office (Jan 2024–Sep 2026; Feb 2024 missing), PUMS 2020–24 for Cook (36 PUMAs, all inside Cook, 196k persons), TIGER shapes, and the ZCTA–county file

Blocked: ACS ZCTA/county tables (B01003, B22003, C27007, B05001) need the Census API key.

Next:
1. `01_snap_series.py`: parse IDHS office HTML → monthly Cook persons/households, Chicago vs. suburban; reconcile with the Sept 2025 county PDF; counterfactual trend.
2. `02_pums_shares.py`: ACA-like universe → exemptions → subject share (a) and (b).
3. Parse the CCH deck (ACA capitation, members, charity care, payer mix) and the HFS zip PDF.
4. Medicaid model, SNAP model, zip allocation, charts/maps, methods.md.

## Open questions
- No cited source yet for the 19/30/40% loss rates
- Share of Cook SNAP households affected by the LIHEAP/utility-allowance change
- HFS statewide ACA cost per member
- The extra-churn and 2028 verification parameters are placeholders
