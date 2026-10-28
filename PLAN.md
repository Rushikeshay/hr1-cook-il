# H.R. 1 impact on Cook County, IL — Medicaid and SNAP (2026–2028)

Revised plan, 2026-10-27. Supersedes `hr1_cook_claude_code_prompt.md` where they differ.
Every number in the analysis is labeled **observed** (published count), **derived** (computed from observed data), or **assumed** (parameter we chose).

## Scope of "money leaving the county"
Report dollars in three separate buckets, never summed silently:
1. **Federal dollars lost** because of H.R. 1 (main headline).
2. **State dollars lost to Cook residents** where the state pulls back *as a direct result of H.R. 1* (e.g., state share of Medicaid for people disenrolled; any state program cut tied to H.R. 1 costs).
3. **New state costs** caused by H.R. 1 (SNAP admin 75%, SNAP benefit cost share, implementation costs), shown as Cook's proportional share. These are a budget pressure, not money leaving residents' pockets.

## Confirmed facts (Step 0 results)

### Medicaid
| Fact | Value | Status | Source |
|---|---|---|---|
| Cook ACA adults, June 30 2025 | 364,204 | observed | HFS Cook enrollment page (FY2025) |
| Cook total Medicaid, June 30 2025 | 1,535,983 | observed | same |
| HFS "ACA adult" definition | 19–64, no Medicare, no dependent child <18 in home | observed | HFS work-requirement FAQ / Sept 2026 notice |
| Work requirement effective | Jan 1 2027 (applications after 5pm Dec 31 2026) | observed | IDHS item=180030; HFS FAQ |
| First compliance checks | Redeterminations due March 2027 | observed | IDHS item=180030 |
| Lookback | ≥1 compliant month in the 6 months before renewal | observed | HFS Sept 2026 notice |
| Response window | 30 days → first losses ~April 2027 | derived | HFS notice |
| Renewal frequency for ACA adults | Every 6 months after first 2027 renewal (exempt people too) | observed | HFS |
| Ways to comply | 80 hrs/mo work, volunteering, work program, half-time school, or income ≥ $580/mo | observed | HFS draft materials |
| Noncitizen Medicaid loss | ~9,300 statewide, effective Oct 1 2026 (refugees, asylees, trafficking survivors, etc.) | observed | Get Covered Illinois press release 10/14/2026 |
| Federal match, ACA adults | 90% | observed | statute |
| HFS zip file | FY2025, **total enrollees only** (no category split) | observed | HFS zip page |

### SNAP
| Fact | Value | Status | Source |
|---|---|---|---|
| Illinois ABAWD waiver ended | Jan 31 2026; time-limit clock started Feb 1 2026 | observed | IDHS item=175082 |
| First cutoffs | May 1 2026 | observed | IDHS FAQ item=176106 |
| 36-month period | **Fixed**, Jan 1 2024 – Dec 31 2026; new period Jan 1 2027 | observed | IDHS |
| Second wave | Countable months Jan–Mar 2027 → cutoffs ~April 1 2027 | derived | from fixed period |
| Time-limited adult definition | 18–64, no child <14 in household, not exempt | observed | IDHS |
| Noncitizen SNAP cut | Implemented April 1 2026 (refugees, asylees, etc.) | observed (date); count assumed 14,000–16,000 statewide (advocacy estimates) | IDHS / Greater Chicago Food Depository / Borderless |
| LIHEAP → utility allowance change | New criteria from Sept 26 2025; existing cases at next redetermination. Households without an elderly/disabled member lose automatic heating/cooling SUA ($565 standard) | observed | IDHS MR / PM 13-01-08-b |
| Internet cost excluded from SUA | in law; IL effective date to confirm | observed (rule), date TBD | P.L. 119-21, CRS R48552 |
| IL payment error rate FY2025 | 14.67% (13.33% over / 1.33% under); FY2024 was 11.56% | observed | USDA FY2025 QC report |
| Benefit cost share (15%) | **Delayed**: since 14.67% ≥ 13.34%, starts FY2029 (Oct 1 2028) at earliest; FY2030 (Oct 2029) if the FY2026 rate is also ≥ 13.34% | observed rule; start year is a scenario | CivicFed, NPR Illinois |
| Admin cost share | 75% state from Oct 1 2026 (~$80M/yr statewide) | observed | CivicFed |
| Avg benefit | $195/person/month (May 2026); replace with IDHS issuance $ if available | observed (secondary) | CivicFed |

## Method changes vs. the original prompt

### Medicaid
1. **PUMS universe matches the HFS ACA category**, not "all low-income adults": Cook PUMAs, age 19–64, Medicaid (HINS4), POVPIP ≤ 138, **no Medicare (HINS3)**, **no SSI (SSIP > 0)**, **not a parent/caretaker of a child <18 in the household**.
2. **Exemptions (full H.R. 1 list, with PUMS proxies):** pregnant/postpartum (FER), disability as a proxy for medically frail (DIS), veteran with a disability rating (MIL + DRAT), American Indian / Alaska Native (RACAIAN), caregiver of a disabled household member (proxy), half-time student (SCH), meets SNAP/TANF work rules (PAP > 0 + working, proxy). Groups with no proxy (SUD treatment, recently incarcerated, former foster youth) are a parameter.
3. **Already compliant:** WKHP ≥ 20 and worked in the past 12 months, **or** earnings ≥ $580/month (PERNP/12). Both versions reported.
4. **Shares reported:** (a) subject = not exempt; (b) subject and not already compliant. (a) is the headline.
5. **Losses** = baseline × subject share × loss rate (19/30/40%, each with its source and base recorded), **plus** "exempt but lost on paperwork" = baseline × exempt share × paperwork-loss rate (parameter, default low), **plus** extra churn from 6-month renewals (parameter).
6. **Timeline:** renewals spread evenly across months starting March 2027; losses start April 2027; the second 6-month cycle starts Sept 2027 onward. 2028 verification increase is a parameter.
7. **Noncitizens:** 9,300 × Cook share (derive from ACS Cook share of Illinois noncitizens; note as derived).
8. **Dollars:** member-months lost × PMPM. Two PMPM estimates: CountyCare ACA (CCH FY27 deck) and HFS statewide ACA adult. Split into federal 90% / state 10%.
9. **Zip allocation:** HFS zip totals only cover total enrollees, so distribute by total enrollees **adjusted by** ACS C27007 share of Medicaid enrollees aged 19–64 per ZCTA. Report both versions.
10. **Not H.R. 1 (excluded, noted):** loss of the Illinois HBIA program (state decision); expiry of enhanced Marketplace subsidies.

### SNAP
1. Monthly Cook series Sept 2025 → latest IDHS month (persons, households, Chicago vs. suburban by office). Reconcile against the county PDF; flag any gaps.
2. **Counterfactual:** compare against the same months a year earlier and the pre-Feb 2026 trend. Report the *observed drop* and the *drop beyond trend (attributed to H.R. 1)* separately. Note the Nov 2025 shutdown disruption.
3. **Second wave (April 2027):** PUMS time-limited adults still on SNAP × loss rate calibrated to the observed May 2026 drop.
4. **Noncitizens:** statewide estimate × Cook share.
5. **Benefit cuts for people who stay on (new):**
   - LIHEAP/SUA: affected households (SNAP households with no elderly/disabled member that got the SUA via LIHEAP) × benefit reduction (30% × drop in shelter deduction, capped). Phased in at redeterminations from Sept 2025.
   - Internet exclusion: the effect is small or zero if Illinois never included internet in its SUA; confirm.
   - Thrifty Food Plan cost-neutrality: future COLA restraint; parameter.
6. **Dollars:** persons lost × avg benefit, plus benefit cuts. All federal.
7. **State cost share:** scenarios for FY2029 or FY2030 start; Cook share = Cook share of Illinois SNAP benefits. Admin 75% from Oct 2026. These are reported as new state costs (bucket 3).
8. **Zip allocation:** ACS B22003 SNAP households per ZCTA.

## Data inputs (download test 2026-10-27)
Downloads of the IDHS, HFS and CCH files all succeed with a browser user agent, so **no manual downloads should be needed**.
| # | Dataset | Status |
|---|---|---|
| 1 | HFS Cook enrollment FY21–25 | page reachable; FY2026 not yet posted |
| 2 | HFS FY2025 enrollment by zip (PDF, totals only) | downloads |
| 3 | CCH Prelim FY27 budget deck | downloads |
| 4 | IDHS SNAP county PDF, Sept 2025 | downloads |
| 5 | IDHS SNAP by servicing office, monthly | pages reachable (June 2026 confirmed; find latest) |
| 6 | ACS PUMS 2020–2024 5-year, Illinois | Census API / FTP |
| 7 | ACS 2020–2024 5-year ZCTA (B22003, C27007, B01003); B05001 for noncitizen share | Census API |
| 8 | TIGER ZCTA + county + Chicago place boundary | Census |
| 9 | HUD USPS ZIP–tract crosswalk (for ZIP↔ZCTA and the Cook portion of border zips) | HUD (may need a free API token) |

## Repo structure
```
data/raw/  data/processed/  src/00_fetch.py … src/NN_*.py
params.yaml  output/figures/  output/tables/  methods.md
```
Python env: conda `BED` (added geopandas, pyogrio, pyyaml, requests, pdfplumber, openpyxl).

## Outputs
As in the original prompt (charts 1–5, maps 6–8, tables), with additions:
- Chart 1 gets a counterfactual trend line.
- Charts 3–4 add "benefit cuts (still enrolled)" for SNAP.
- Chart 4 splits dollars into the federal, state-pullback and new-state-cost buckets.

## Open questions
1. Is the FY2026 IL SNAP error rate (released ~June 2027) unknown? If so, cost-share start stays a two-scenario parameter.
2. Did Illinois ever include internet costs in its SUA?
3. Exact Cook share of the 9,300 Medicaid and ~15,000 SNAP noncitizen losses (no county breakdown published).
4. Loss-rate sources for 19/30/40%: confirm the base (subject vs. all expansion adults) of each.
