# Step 9: independent recompute of headline numbers

Date 2026-11-03. Recomputed from `data/raw/` using only PLAN.md, methods.md and params.yaml. I wrote my numbers down
before opening `output/ledger.csv` or `src/`. My code is in this folder: `txt.py` (HTML text), `snap_series.py`,
`snap_calc.py`, `pums.py`, `model.py`, `overlap.py`.

## Results (Dec 2028 unless noted; low / mid / high)

| Number | Mine | Project | Diff | Verdict |
|---|---|---|---|---|
| HFS Cook ACA adults, Jun 2025 | 364,204 | 364,204 | 0% | match |
| IDHS Cook SNAP persons Sep 2025, county PDF | 881,937 | 881,937 | 0% | match |
| IDHS Cook subtotal Sep 2025, office page (Jun 2026 anchor 686,905 also reproduced) | 851,244 | 851,244 | 0% | match |
| SNAP pre-trend, %/month (log-linear, Jan 2024-Jun 2025) | -0.2400% | -0.2400% | 0% | match |
| SNAP H.R. 1 persons lost by Sep 2026, low | 135,258 | 134,271 | +0.7% | match |
| ... mid | 188,541 | 188,436 | +0.1% | match |
| ... high | 217,895 | 217,895 | 0% | match |
| SNAP persons off Dec 2028, low | 161,430 | 156,162 | **+3.4%** | judgment call (see 1) |
| ... mid | 229,448 | 226,947 | +1.1% | match |
| ... high | 272,594 | 272,236 | +0.1% | match |
| Federal SNAP benefits 2028, mid | $536.9M | $531.1M | +1.1% | match |
| Medicaid off coverage, low | 98,785 | 98,785 | 0% | match |
| ... mid | 165,827 | 165,827 | 0% | match |
| ... high | 213,173 | 213,173 | 0% | match |
| Federal Medicaid $ 2028 (CountyCare PMPM $836.10 x 90%), mid | $1.354B | $1.354B | 0% | match |
| Lose both programs, mid (central) | 24,632 | 34,395 | **-28%** | my method cruder; project's is better (see 2) |
| Unique residents affected, mid | 370,643 | 358,379 | **+3.4%** | follows from 2 |

Other values that matched: county/office ratio 1.0361; CCH p25 column order (word positions put 69,768 and $700M under
"ACA Adult"); Cook share of IL noncitizens (ACS B05001) 0.5997; Urban Table A.2 Illinois rows (8/15/15% and
18/29/42%); derived subject loss rates 38/58/82%; PUMS broad ACA-like universe 297,849 (82% of HFS); share (a)
0.471 vs project 0.481 (I also took off the 2% unmodeled exemptions; no effect on totals, see below).

## Causes of gaps over 2%

1. **SNAP low, wave 2 (+3.4%).** My second-wave low is 26.2k, the project's 21.9k. The only difference is the PUMS
   time-limited share of SNAP persons: mine 14.3%, the project's 12.7%. The project also treats students (SCH 2/3)
   and employed TANF recipients as exempt; I did not, but I exempted SSI recipients. Both are defensible proxies.
   Students have their own SNAP rules, so the project's choice is, if anything, the better one. Neither side is
   wrong. The share cancels out in the high scenario (wave 2 = calibration excess x Sep/Apr 2026 caseload) and
   mostly cancels in mid. Wave-1 differences under 1% come from how the trend is applied: the project adds
   r x the *observed* prior month, while I compound r from the base month. Both are fine.
2. **Overlap (-28%).** I gave every SNAP person the same chance of losing SNAP. The project gives time-limited
   adults (childless, 18-64, the same people as ACA adults) a much higher chance, and takes min(pM, pS) person by
   person. The project's method is more realistic; mine understates the overlap. This is a range estimate in any
   case (project low-high 19k-44k for mid).

## Errors or questionable choices found

No arithmetic or coding errors found in the headline chain. Points worth a note in methods.md:

- **Wave-2 SNAP pool is fragile.** The May-June 2026 excess (62k) is 58-65% of the PUMS time-limited pool, which
  *includes* people working 30+ hrs/week (exempt from the time limit under 7 U.S.C. 2015(o)(3)(D)/(d)(2)). With a
  stricter pool (no 30h+ workers, no students; 46k) the implied rate is over 100%. So either the May-June excess
  includes losses not caused by the time limit, or PUMS undercounts the pool (the project already notes the PUMS
  pool is 46% of IDHS's 450k x Cook share). The "survivors" pool in the low scenario, pool minus 62k, is the piece
  most sensitive to this: 0-26k depending on the definition. Suggest saying so next to the low SNAP number.
- **Medicaid totals do not depend on PUMS.** Total work-requirement loss = Urban share x 364,204 by construction.
  The subject share only splits it into subject and exempt-paperwork losses. That makes the result robust, but
  the paperwork rates (0/3/6%) and share (a) change nothing in the headline. Worth stating so readers don't
  over-read the PUMS work.
- **Renewal losses x baseline (not x people still enrolled).** This matches Urban: both Table A.2 shares are of
  baseline, and the work-requirement share is "incremental after six-month redetermination". Applying renewals to
  people still enrolled would give 93k / 149k / 189k, 6-11% lower. The project's choice is correct per the source.
- **Noncitizen Medicaid cut (minor).** The 9,300 statewide figure covers all Medicaid noncitizens, not only ACA
  adults. Counting the Cook share (4.1-5.6k) as ACA adults at the ACA PMPM slightly overstates the ACA-adult loss
  and its dollars (under 0.5% of federal dollars).
- **Specialty-office break.** Ending the trend fit in June 2025 correctly avoids the July 2025 break. But
  statewide specialty-office persons fell from 22.4k (Dec 2025) to 11.4k (Sep 2026). If any of those were Cook
  residents moving back into Cook offices, the Cook drop is slightly *understated*. Small, and the direction is
  unknown.

## Bottom line

Working only from the raw files and params.yaml, I reproduce every Medicaid headline number exactly (99k / 166k /
213k off coverage; $1.354B federal in 2028, mid). SNAP matches within about 1% for mid and high (227k / 272k off;
$531M federal in 2028, mid). The only gap above 2% is SNAP low (156k vs my 161k), which comes from a different but
equally defensible proxy for who is time-limited. My rougher overlap method gives a lower count of people losing
both programs; the project's method is the better one. I found no errors in the project's arithmetic or code
along the headline chain. The main fragility is a modeling one: the second-wave SNAP calibration implies a 58-65%
loss rate over a PUMS pool that is probably too small, so the low SNAP scenario's second wave deserves a
sentence of caution.
