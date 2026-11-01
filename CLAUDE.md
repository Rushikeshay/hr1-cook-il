# H.R. 1 impact on Cook County — Medicaid & SNAP

Estimates how many Cook County, IL residents lose Medicaid or SNAP (or get smaller SNAP benefits) because of H.R. 1, and how many dollars leave the county, 2026–2028. Results by year, program, scenario, and zip code.

- **[PLAN.md](PLAN.md)**: the agreed plan, confirmed facts with sources, and method decisions. Read it first.
- **[params.yaml](params.yaml)**: every number and assumption, each labeled `observed` / `derived` / `assumed` with a source. Change scenarios here, never in code.

## Environment
- Python (Mac, 2026-10-31): conda env **hr1** → `/opt/miniconda3/envs/hr1/bin/python`.
- Python (Windows work machine): conda env **BED** → `C:\Users\rushikeshjadhav\AppData\Local\miniconda3-pbe\envs\BED\python.exe` (not on PATH). On another machine, create an env with pandas, geopandas, pyogrio, matplotlib, pyyaml, requests, pdfplumber, openpyxl, truststore (conda-forge).
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

## Status (2026-10-29: Steps 0-7 + overlap done)
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
  params six_month_renewal_loss), replacing the unsourced 0/2/4% placeholder; x baseline (additive with Urban's
  work-requirement piece, which is measured after renewals). Work-req rates: see "Medicaid loss rates" below.
  HFS PMPM still missing (dollars use CountyCare $836 only).
  Urban/RWJF (Mar 2026) is the source of CCH's "400k" (= Illinois low mitigation 415k; parsed in 01f).
  User rule: keep our method; use Urban to correct weak spots and as a cited comparison.

- Step 6 `05_snap.py`: wave 1 = step 3 observed beyond-trend loss, held flat after Sept 2026 (noncitizen cut is
  an "of which", ~12k mid). Wave 2 (Apr 2027): rate = May-June 2026 excess (62k office; params
  snap.time_limit.calibration_window) / PUMS time-limited pool Apr 2026 (96k) = 64.5%.
  Decision 2026-10-28: wave-2 pool by scenario (params second_wave_pool): low = wave-1 survivors (23k lost),
  mid = midpoint (39k), high = refilled pool per PLAN (54k). Multipliers set to 1.0.
  Off SNAP Dec 2028: low 156k / mid 227k / high 272k. Federal benefits lost (mid): 2026 $320M, 2027 $508M,
  2028 $531M. State costs (bucket 3, Cook 47.5%): admin $38M/yr from Oct 2026; 15% benefit share Oct-Dec 2028
  ~$55M (early) or $0 (late).
  LIHEAP/SUA: affected = no 60+/disabled member AND got A/C-Heat standard only via LIHEAP (no own heat/AC bill).
  IDHS standards verified from raw pages (FY26 $546/$457/$78/$67, FY27 $565/$472/$80/$69). Cut per household
  (upper bound) = 0.30 x (A/C-Heat - fallback): $28/mo (limited, low/mid), $149/mo (phone only, high).
  Household count not published -> dollars not estimated (table gives $ per 10k households).
  Triangulation: first wave 64k vs IDHS 148k x Cook = 70k (0.91); PUMS pool is 46% of IDHS's 450k x Cook.

  Decision 2026-10-28: LIHEAP/SUA and internet SNAP benefit cuts are OUT OF SCOPE for totals (small: ~1-3% of SNAP $);
  described in methods.md (started; scope notes only). LIHEAP per-household cut table kept for reference.
- Step 7 `06_zip_alloc.py`: 177 ZCTAs (Cook portion). Medicaid key = HFS ACA adults by zip (alt: ACS C27007 19-64;
  correlation 0.98); SNAP key = ACS B22003 SNAP households. Zip totals = county totals exactly. 21 border ZCTAs
  flagged; 7 ZCTAs < 1,000 residents get blank per-resident rates (e.g. 60141 Hines VA). Mid 2028: Chicago 103k
  Medicaid / 149k SNAP; suburban 63k / 78k. Outputs: output/tables/zip_results_long.csv, zip_results_2028_mid.csv,
  region_results_mid.csv. Tracers: 60623 -> 4,243 Medicaid / 5,594 SNAP; 60426 -> 1,541 / 2,302 (mid, Dec 2028).
- Step 6b `05b_overlap.py`: people losing BOTH programs (never add Medicaid + SNAP people). PUMS joint
  probabilities by group, scaled to county totals; range = independent (low) to fully correlated (high), central =
  midpoint. 44% of ACA-like adults live in SNAP households (HFS: "about half of Medicaid customers are SNAP
  recipients"). Output: output/tables/medicaid_snap_overlap.csv; ledger ids ovl_*.

## Audience and output (decided 2026-10-29)
- Author/publisher: the user, Applied Data Fellow with the Cook County Bureau of Economic Development. Audience:
  Bureau staff, internal and external. Question it answers: "With H.R. 1, how many more residents will rely on the
  county, and can we handle it?" Helps staff imagine the future; not the final answer.
- Scrollytelling article, PLAIN JS (scrollama + D3), "NYT-style" look only (no NYT branding). Desktop/laptop
  first; must still work on mobile.
- LEAD WITH THE RANGE: show low/mid/high and how each was built; don't push one number.
- No human-voice reporting or agency comments; the user edits the prose and sends the finished piece to county
  officials for review/fact-check.
- Draft section order: zip hook (60623) -> SNAP observed vs trend -> Medicaid dot grid peeling off by cause ->
  "working and still lose coverage" (share a 48% vs b 21%) -> three-bucket money flow -> zip map per 1,000
  residents -> county ripple (CCH charity care / revenue) -> scenarios + Urban comparison -> methods + data download.

## Medicaid loss rates (decided 2026-10-29)
- The old 19/30/40% came with the original prompt ("user-supplied", never sourced). REPLACED.
- Now: work-req + exempt-paperwork losses = Urban/RWJF Illinois work-requirement share of ALL ACA adults, 18/29/42%
  (low/mid/high = Urban high/medium/low mitigation); renewals 8/15/15% x baseline (additive in Urban).
  Derived subject loss rates 38/58/82%. 2028 verification add-on set to 0 (inside Urban's figure).
- `01g_il_vs_urban.py`: Illinois's announced choices match Urban's HIGH-mitigation setting on all 5 decided
  dimensions (1-month compliance, self-attestation, NSC student data, shared HFS-DHS system, broad frailty); every
  quote auto-checked against raw docs. Enrollee response (65/75/87% non-response; Arkansas/NH roots) drives the range.
- Root sources downloaded: Urban report, Sommers 2019 NEJM, Brookings Arkansas paper (likely Urban's "Fiedler 2025"),
  KFF integration table (lists IL as not integrated for SNAP, contradicting HFS FAQ), HFS Module 3/FAQ/notice.
  Full citation chain in methods.md. HFS internal estimate 165-330k of 700k (24-47%): triangulation only.

## Headline results (2026-10-29, Dec 2028, low / mid / high)
- Off Medicaid: 99k / 166k / 213k (Chicago 103k, suburban 63k in mid). Federal Medicaid $ 2028 mid $1.35B
  (state 10% separate: $150M).
- Off SNAP: 156k / 227k / 272k. Federal SNAP $ 2028 mid $531M.
- Both programs: 19k / 34k / 44k. Different residents affected: 236k / 358k / 441k.

## Who is at risk (step 4b `03b_profiles.py`, 2026-10-29)
- ACS PUMS 2020-24 Cook adults in each at-risk group (same rules as step 4), replicate-weight SEs. PUMS re-cut adds
  SEX, HISP, RAC1P, SCHL, ENG, LANX. Chicago vs suburban by PUMA (tract share in Chicago); PUMAs 03109 (13%) and
  03164 (84%) are mixed (soft WARN). Describes people AT RISK (pre-H.R. 1 survey), not people who actually lost coverage.
- Subject to Medicaid work req: 49% didn't work in past 12 months, 42% worked 20+ hrs/wk; 37% Black (vs 21% of all
  Cook adults 19-64); 62% Chicago. Subject and not working enough: 49% Black, 39% aged 50-64. SNAP time-limited:
  53% Black; time-limited and not working: 49% aged 50-64. Output: output/tables/pums_profiles(_wide).csv.

## County pressure (step 6c `05c_county_pressure.py`, 2026-10-29)
- Public figures only (no internal decisions). CountyCare share of Cook ACA adults 19.2% (CCH FY27 69,768 / HFS
  364,204; assumed same loss rate). CountyCare ACA capitation lost, Cook FY (Dec-Nov): FY2027 $40M / $64M / $86M;
  FY2028 $167M / $277M / $365M (low/mid/high). Members off end FY2028: 19k / 32k / 41k.
- County's own FY2027 forecast (press release, downloaded + quotes auto-checked): Health Fund revenue -$486.5M "due
  to a significant expected decrease in CountyCare membership" (all programs, federal cuts + Medicare eligibility);
  $138.0M OBBBA fallout for the hospital system; $214.7M Health Fund gap. Our FY2027 H.R. 1 ACA piece is far
  smaller than -$486.5M: ask county officials what drives it (all programs, reprocurement?, timing).
- SNAP local economy (USDA ERS ERR-265: $1.54 GDP per $1, 13,560 jobs per $1B; national, illustrative): mid
  2028 $818M activity, ~7,200 jobs.
- Not usable: IDPH hospital-level charity care (raw questionnaire not public; profiles not found); HFS monthly MCO
  reports (nothing after June 2024 found). CCH charity care history from the CCH deck is in
  output/tables/cch_charity_care_history.csv.

## Step 8 outputs (2026-10-29)
- `07_outputs.py`: output/story/story_data.json (headline numbers keep ledger ids; full ledger included),
  output/story/cook_zcta.geojson (Cook-clipped, simplified, GeoJSON not TopoJSON: no topojson lib in env),
  output/figures/fig1-5 PNG + CSV (SNAP vs trend, Medicaid scenarios, residents affected, 3 dollar buckets as
  separate panels, Medicaid/SNAP zip maps). Colors: Medicaid blue / SNAP orange / both aqua; scenarios blue ramp.
- `07b_story_preview.py`: story/template.html (EDIT THIS) -> output/story/preview.html (generated, single file,
  data inlined). Text numbers are [data-id] spans filled from the ledger; build fails on unknown ids.
  Plain JS: d3 7.9.0 (cdnjs) + scrollama 3.2.0 (jsdelivr). Fonts: Newsreader (serif) + Libre Franklin (sans).
- Comments on the artifact get fixed on the published page only: pull the live page back into story/template.html
  (replace the inlined data line with /*__DATA__*/) before rebuilding, or the fixes are lost.
- 2026-10-31: preview now 4 of 9 sections: SNAP -> Medicaid timeline (stacked by cause, low/high at end) -> people
  grid (1 figure = 1,000 ACA adults; subject / not 80 hrs / lost by cause, mid -> low -> high) -> both programs + map.
  Medicaid cause colors: noncitizen magenta, work req blue (incl. exempt paperwork), renewals yellow (validated).
- Private preview: https://claude.ai/artifact/SFEYHaPxUA2wF4DA51NR6Y
  Republish = rebuild preview.html, then publish the same file path.

Next:
1. User reviews the preview; then build the remaining sections (who is at risk, Medicaid timeline/dot grid,
   "working and still lose coverage", money in three buckets, county pressure, scenarios + Urban comparison,
   methods + data download).
2. Step 9 independent recompute before publishing.

## Open questions
- Urban's shares are 2028 levels net of re-enrollment; we hold them flat through Dec 2028 (no further dynamics)
- Not modeled separately: new applicants denied by the work requirement (Urban includes them in its shares)
- HFS statewide ACA cost per member (second dollar estimate)
