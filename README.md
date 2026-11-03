# H.R. 1 in Cook County: Medicaid and SNAP, 2026-2028

How many Cook County, Illinois residents lose Medicaid or SNAP because of H.R. 1 (the One Big Beautiful Bill Act,
2025), where they live, and how much money leaves the county. Results by year, program, scenario and zip code.
Data through September 2026.

Prepared by Rushikesh Jadhav, Applied Data Fellow, Cook County Bureau of Economic Development.

## Results (December 2028, low / middle / high scenario)

| | Low | Middle | High |
|---|---|---|---|
| Residents who lose Medicaid, SNAP or both (each counted once) | 236,000 | 358,000 | 441,000 |
| Lose Medicaid (ACA expansion adults) | 99,000 | 166,000 | 213,000 |
| Lose SNAP | 156,000 | 227,000 | 272,000 |
| Federal dollars lost in 2028 (Medicaid + SNAP) | $1.18B | $1.89B | $2.41B |

SNAP's losses have already happened (by September 2026, 134,000-218,000 fewer residents were getting SNAP because of
the law). Medicaid's are projections: the work requirement starts in 2027.

## Where to look

- **The article:** https://rushikeshay.github.io/hr1-cook-il/ (GitHub Pages, served from `docs/index.html`; the same
  file as `output/story/preview.html`).
- **Method, sources and limitations:** [methods.md](methods.md).
- **Every assumption, with its source:** [params.yaml](params.yaml).
- **Every number, with its formula and inputs:** `output/ledger.csv`. `python src/trace.py <id>` shows any number's
  lineage back to the raw files.
- **Tables:** `output/tables/` (zip-level results: `zip_results_long.csv`, `zip_results_2028_mid.csv`).
- **Charts:** `output/figures/` (PNG plus the CSV behind each).
- **Checks:** `output/checks/report.md`; independent recompute: `output/checks/independent/independent_review.md`.

## Run it

1. Python environment with pandas, geopandas, pyogrio, matplotlib, pyyaml, requests, pdfplumber, openpyxl,
   truststore (conda-forge).
2. Free Census API key in `.env`: `CENSUS_API_KEY=...` (see `.env.example`).
3. `python src/00_fetch.py` downloads all sources to `data/raw/` (about 180 MB; not in the repo).
4. `python src/run_all.py` runs every step and stops at the first failed check.
5. Tests: `python -m pytest tests -q`.

## Layout

```
src/NN_*.py        one numbered script per step, run in order (src/run_all.py)
src/lib/           checks, ledger, tracer, PUMS rules
data/raw/          downloads, untouched (gitignored)
data/processed/    cleaned intermediate tables
output/            ledger, tables, figures, checks, article
story/template.html  article source (numbers filled from the ledger at build time)
```

`PLAN.md` is the original planning document, kept for the record; `methods.md` is current.
