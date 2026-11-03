# Methods

How this study estimates H.R. 1's effect on Medicaid and SNAP in Cook County, Illinois, 2026-2028. It has enough
detail to reproduce every number. All parameters, with their sources, are in `params.yaml`. Every number in the
article is a row in `output/ledger.csv`, labeled **observed** (published figure), **derived** (computed here) or
**assumed** (a scenario choice). `python src/trace.py <id>` prints any number's full lineage back to the raw files.

Data cutoff: September 2026 (latest IDHS SNAP month); sources retrieved October 27-November 3, 2026.

## 1. Reproducing the analysis

1. Create a Python environment with pandas, geopandas, pyogrio, matplotlib, pyyaml, requests, pdfplumber,
   openpyxl and truststore (conda-forge).
2. Put a free Census API key in `.env` as `CENSUS_API_KEY=...` (template: `.env.example`).
3. `python src/00_fetch.py` downloads every source to `data/raw/` (about 180 MB). IDHS pages need a browser
   User-Agent, which the script sends.
4. `python src/run_all.py` runs every step in order and stops at the first failed check. Results of all checks:
   `output/checks/report.md`. Unit tests: `python -m pytest tests -q`.
5. `python src/07b_story_preview.py` builds the article (`story/template.html` -> `output/story/preview.html`).

| Step | Script | What it does |
|---|---|---|
| 1 | `00b_manifest.py` | Records URL, size and SHA-256 of every raw file; flags files that changed between runs |
| 2 | `01a`-`01g` | Parses IDHS, HFS, CCH, Census and Urban Institute sources into tidy tables; checks published totals |
| 3 | `02_snap_series.py` | Cook SNAP monthly series, pre-H.R. 1 trend, losses beyond trend |
| 4 | `03_pums_shares.py`, `03b_profiles.py` | Shares and profiles from Census microdata (PUMS) |
| 5 | `04_medicaid.py` | Medicaid losses by month, cause and scenario; dollars |
| 6 | `05_snap.py` | SNAP losses through 2028; dollars; new state costs |
| 6b-d | `05b_overlap.py`, `05c_county_pressure.py`, `05d_both_profile.py` | People losing both programs; county budget facts; who loses both |
| 7 | `06_zip_alloc.py` | Splits county totals across zip areas |
| 8 | `07_outputs.py`, `07b_story_preview.py` | Charts, tables, article data |

## 2. Scenarios

Three scenarios, low / middle / high, differ mainly in how many eligible people lose benefits because they do not
complete the new paperwork. The middle scenario is the central estimate; the article always shows the range.

- **Medicaid:** low / middle / high = the Urban Institute's high / medium / low "mitigation" settings for Illinois
  (Section 4).
- **SNAP:** the scenarios differ in which month counts as the start of H.R. 1's effect, and in how many adults the
  April 2027 cutoffs can reach (Section 3).

## 3. SNAP

**Monthly series.** IDHS "SNAP Data by Servicing Office" pages, January 2024-September 2026, Cook County subtotal row
(persons). February 2024 was not published. IDHS reports Cook only as one subtotal, so there is no Chicago vs.
suburban series. A "Specialty Offices" subtotal begins July 2025, a break in the series; the baseline month is
September 2025.

**Residents vs. offices.** The office table counts cases by servicing office; IDHS's county PDF counts residents.
In September 2025 they differ: 881,937 residents vs. 851,244 by office (ratio 1.036). Middle and high scenarios
scale office-based changes to residents by this ratio; the low scenario does not.

**Trend without H.R. 1.** Log-linear fit to January 2024-June 2025 (before the law was signed and before the
reporting break): -0.24% a month. It is extended forward from September 2025.

**Losses so far (to September 2026).** Persons below the trend, counted from a scenario start month:

| Scenario | Counting starts | Why |
|---|---|---|
| Low | February 2026 | Time limit legally began (IDHS IM, January 15, 2026) |
| Middle | December 2025 | IDHS first applied H.R. 1's work requirement |
| High | October 2025 | Every month after the baseline; flat trend |

The April 2026 noncitizen cut (IDHS estimate, 20,000 statewide, times Cook's share of Illinois noncitizens) is
inside these totals, shown as an "of which".

**April 2027 cutoffs.** The 36-month period is fixed (January 2024-December 2026). In the new period, adults under the
time limit use up three countable months January-March 2027 and are cut off April 1, 2027.
- Loss rate = excess drop beyond the middle trend in May-June 2026 (62,000, office basis) / adults under the time
  limit in April 2026 (PUMS share 12.7% of SNAP persons x the April 2026 caseload) = 64.5%.
- Pool in March 2027: low = adults who survived the first cutoffs; high = pool refilled to its 2026 size; middle =
  average of the two. Caseload held flat at September 2026 otherwise.

**Dollars.** Person-months lost x average benefit, $195 per person per month (Illinois, May 2026; Civic Federation).
All federal.

**New state costs (Cook share).** From October 1, 2026 the state pays 75% of SNAP administration instead of 50%:
about $80 million a year statewide (Civic Federation) x Cook's share of Illinois SNAP recipients (47.5%, IDHS county
report, September 2025).
Illinois's FY2025 payment error rate (14.67%) means a 15% benefit cost share, delayed to October 2028 at the
earliest (shown) or October 2029 if the FY2026 rate is also at least 13.34% (then $0 within 2026-2028). These are
state costs, kept separate from federal dollars lost.

**Not included:** benefit cuts for households that stay on SNAP (LIHEAP utility-allowance rule from September 2025;
exclusion of internet costs; Thrifty Food Plan limits). IDHS does not publish the number of affected households; at
20,000-50,000 Cook households the LIHEAP change would be about $7-17 million a year, 1-3% of the SNAP dollars above.
Per-household amounts: `output/tables/snap_liheap_cut_per_household.csv`.

## 4. Medicaid

**Starting count.** 364,204 Cook County ACA expansion adults (HFS, June 30, 2025), held flat.

**Who must report work (Census microdata).** ACS PUMS 2020-2024, Cook County PUMAs, with replicate-weight standard
errors (80 weights, successive-difference formula). PUMS only supplies shares; counts always start from the HFS
figure. Rules (`src/lib/pums_rules.py`, tested in `tests/test_pums_rules.py`):
- Expansion-adult universe: age 19-64, Medicaid or means-tested coverage (HINS4), no Medicare (HINS3), no SSI, not
  the parent or caretaker of a child under 18 in the home. No income filter: annual family income in PUMS does not
  match the monthly test Medicaid uses.
- Exempt (any one): disability (DIS, for medical frailty); gave birth in the past year (FER); veteran disability
  rating 70-100% (DRAT); American Indian or Alaska Native; someone else in the home has a disability (caregiver);
  meets SNAP or TANF work rules (public assistance and employed, or SNAP household and working 20+ hours a week).
  A further 2% are treated as exempt for groups PUMS cannot identify (substance-use treatment, recent incarceration,
  former foster youth).
- Already compliant: usually works 20+ hours a week and worked in the past year, or attends school at least half
  time, or earns at least $580 a month.
- Result: 48% of expansion adults must report work (SE 0.7 points); 21% must report and do not already comply.

**Loss rates.** From the Urban Institute and Robert Wood Johnson Foundation's Illinois estimates for 2028
(Buettgens et al., March 2026, Table A.2), as shares of all expansion adults:

| | Low | Middle | High |
|---|---|---|---|
| Work requirement (incl. exempt adults who cannot document their exemption) | 18% | 29% | 42% |
| Six-month renewals | 8% | 15% | 15% |
| Derived loss rate among adults who must report | 38% | 58% | 82% |

Urban measures the work-requirement piece after renewals, so the two add. Within the work-requirement share, exempt
adults lose 0% / 3% / 6% for missing paperwork (assumed); the rest falls on adults who must report. Urban's shares
are 2028 levels net of re-enrollment and include new applicants turned away; we apply them to existing enrollees and
hold them flat through December 2028.

Why Urban's high-mitigation setting is our low scenario: Illinois has announced all five choices that distinguish
Urban's settings, and each matches the most protective one (`output/tables/illinois_vs_urban_scenarios.csv`; quotes
checked automatically against HFS documents):

| Choice | Urban high / medium / low | Illinois | Source |
|---|---|---|---|
| Months of compliance required | 1 / 3 / 3 | One month | HFS Module 3, p. 11 |
| Self-employment | data or self-attestation / no / no | Self-attestation where data can't verify | HFS Module 3, p. 22 |
| Students found in data | 50% / 20% / none | National Student Clearinghouse | HFS Module 3, p. 19 |
| SNAP data match | 95% / 75% / 67% | HFS and IDHS share one eligibility system | HFS FAQ |
| Medical frailty | broad, self-attested / broad / narrow | Broad, incl. difficulty with daily activities | HFS FAQ |

What Illinois cannot choose is how enrollees respond. Urban assumes 65% / 75% / 87% of people asked to report
manually do not, based on Arkansas and New Hampshire (Sommers et al. 2019), where most of those asked to report did
not, although more than 95% of targeted Arkansas adults were working or exempt.

**Timing.**
- Noncitizen cut: 9,300 statewide (State of Illinois) x Cook's share of Illinois noncitizens (60%, ACS B05001; low
  scenario 44%, CBS Chicago), all on October 1, 2026.
- Work requirement: in effect January 1, 2027. First renewals are spread evenly over 12 months from March 2027; each
  month's losses take effect the next month (30-day response window), so losses start April 2027.
- Six-month renewals: each group's first six-month renewal falls September 2027-August 2028; losses the next month,
  then held.

**Dollars.** Member-months lost x CountyCare's average payment for an expansion adult, $836 a month ($700 million /
69,768 members / 12; Cook County Health FY2027 budget, p. 25), held flat. 90% federal, 10% state (statute). The
CountyCare rate stands in for all plans.

## 5. People losing both programs

Only expansion adults can lose Medicaid here, so overlap = Medicaid losers who also lose SNAP. Each PUMS
expansion adult gets a chance of losing Medicaid (by whether they must report work, scaled to the county rate) and of
losing SNAP (zero unless in a SNAP household; higher if under the time limit). Within each group the two may be
unrelated or move together, so the overlap is a range: low = independent (pM x pS), high = fully correlated
(min(pM, pS)), central = midpoint. Shares come from PUMS; counts come from the county totals. Noncitizens are added
separately. Residents affected = Medicaid + SNAP - both.

**Who is likely to lose both** (`05d_both_profile.py`): the same PUMS adults, each weighted by survey weight x the
central chance of losing both by December 2028. Margins of error from the replicate weights hold the chances fixed,
so they understate total uncertainty. Excludes the noncitizen cut (about 2,000 people).

**Who must report work and who is under the SNAP time limit** (`03b_profiles.py`): weighted PUMS profiles of each
group, with Chicago vs. suburban Cook assigned by each PUMA's population share inside Chicago (two PUMAs are mixed).

## 6. Zip areas

177 ZIP Code Tabulation Areas (ZCTAs) touching Cook County. For ZCTAs crossing the county line, the Cook portion is
weighted by 2020 tract population. County totals are split by each program's key, so zip totals equal county
totals exactly:
- Medicaid: HFS FY2025 ACA adults by zip (Cook portion). Check: ACS Medicaid enrollees aged 19-64 by ZCTA
  (correlation 0.98). 60 Cook-area PO-box zips have no ZCTA; their enrollees are left out of the key.
- SNAP: ACS SNAP households by ZCTA (B22003).
Rates per 1,000 residents use ACS population; seven ZCTAs under 1,000 residents get no rate.

## 7. County budget figures

Public releases only: Cook County FY2027 preliminary forecast (June 17, 2026) and executive budget recommendation
(October 8, 2026); Cook County Health FY2027 budget presentation (July 31, 2026); the county's food and housing
investment (March 11, 2026); Cook County Health releases on Food as Medicine (January 23, 2026) and NACo awards
(September 1, 2026). Every figure is stored in `params.yaml` (`county`) with its exact quote and checked against the
downloaded file on each run. CountyCare payments lost = Medicaid losses x CountyCare's share of Cook expansion adults
(19%: 69,768 / 364,204, assuming the same loss rate) x $836, by county fiscal year (December-November). Local economic
activity from SNAP dollars uses USDA ERS's national multiplier ($1.54 of GDP and 13,560 jobs per $1 billion; ERR-265),
as a sense of scale only.

## 8. Checks

- **Raw-file manifest:** size and hash of every download; changes between runs are flagged.
- **Anchor totals:** parsed data must reproduce published totals (HFS Cook ACA adults; IDHS Cook subtotals and state
  totals; PUMS population vs. ACS; CCH deck figures). A failure stops the run.
- **Invariants:** no missing months, shares between 0 and 1, losses not above the people at risk, zip totals equal
  county totals, low <= middle <= high.
- **Automated spot checks:** samples of each parsed source are re-read with a different method (HTML text search;
  a second PDF engine).
- **Tracers:** two zip areas (60623, 60426), one month, one office and one PUMS household are followed through every
  step (`output/trace/trace_report.md`).
- **Comparison with other estimates:** `output/tables/medicaid_triangulation.csv`, `snap_triangulation.csv`
  (article appendix).
- **Independent recompute:** a separate reviewer recomputed the headline numbers from the raw files without our code
  (`output/checks/independent/independent_review.md`).

## 9. Limitations

- **Medicaid losses are projections.** No work-requirement or renewal losses had happened by September 2026.
- **One study drives the Medicaid range.** Urban's rates rest on two earlier state programs. KFF lists Illinois's
  Medicaid system as not integrated with SNAP, while HFS says they share one system; if HFS is right, Urban's
  Illinois figures assume a weaker data match than Illinois has, and losses could be lower. HFS's own unpublished
  estimate (165,000-330,000 of about 700,000 Illinois expansion adults, 24-47%) is consistent with our middle and
  high scenarios.
- **The SNAP trend comparison** also picks up anything else that changed in the same months, including the late-2025
  federal shutdown. The low scenario's later start month limits this.
- **What happens after people lose benefits** is not modeled: re-enrollment is only what Urban's rates include, and
  we do not estimate how many become uninsured or seek county care.
- **Dollars** use one average payment per person per program, held flat. The 9,300 noncitizen figure covers all
  Medicaid noncitizens, not only expansion adults; pricing them at the expansion-adult rate overstates federal
  dollars by under 0.5%.
- **Medicaid totals do not depend on the PUMS shares.** The work-requirement loss is Urban's share x the HFS count; the
  PUMS subject share and the 0/3/6% paperwork rates only split that total between adults who must report and exempt
  adults. Renewal losses apply to the full baseline, as Urban defines them; applying them only to people still
  enrolled would lower the totals by 6-11%.
- **The April 2027 SNAP cutoffs are the least certain SNAP piece.** The calibration rate (May-June 2026 excess drop /
  PUMS time-limited pool = 64.5%) is high, which suggests either that the excess drop includes some losses not caused
  by the time limit or that PUMS undercounts the pool (it is about half IDHS's estimate). With a stricter pool
  definition the implied rate passes 100%, so the low scenario's pool of adults who survived the first cutoffs could
  range from near zero to about 26,000. Treat the second wave as an order of magnitude.
- **PUMS shares** describe 2020-2024 and use proxies for exemptions.
- **Specialty offices:** statewide SNAP persons served at specialty offices fell from about 22,000 to 11,000 between
  December 2025 and September 2026. If some were Cook residents moving back to Cook offices, the Cook drop is slightly
  understated.
- **Zip results** are allocations, not observed counts.
- **Not included:** new applicants turned away by the Medicaid work requirement (beyond Urban's shares); SNAP benefit
  cuts for people who stay enrolled; H.R. 1's changes to Medicaid financing (provider taxes, state-directed payments);
  the end of enhanced Marketplace subsidies and Illinois's own program decisions, which are not H.R. 1.

## 10. Sources

Full citations are in the article's Sources list; download URLs for every raw file are in `src/00_fetch.py` and
`data/raw/_sources.json`. Main sources: H.R. 1 (Public Law 119-21); IDHS SNAP office and county reports, notices and
FAQ; HFS Cook enrollment, enrollment by zip, HR1 webinar Module 3, FAQ and customer notice; State of Illinois
noncitizen release; Cook County Health FY2027 budget presentation; Cook County budget releases; Urban Institute/RWJF
(Buettgens et al. 2026); Sommers et al. 2019 (NEJM); KFF eligibility-system integration table; Civic Federation;
USDA ERS ERR-265; Census ACS 2020-2024 (tables and PUMS) and 2020 geography files.
