# Methods and limitations

*Draft. The full write-up is Step 9; this file collects scope decisions as they are made.*

## Scope

The analysis covers the two programs that reach the most Cook County residents and put the most pressure on county
resources when federal support is cut: **Medicaid** (ACA adults) and **SNAP**. For each, it counts people who lose
coverage or benefits because of H.R. 1 and the dollars that go with them, plus new costs the state must pick up.

### Smaller H.R. 1 SNAP changes, not modeled

These rules lower benefits for some households that stay on SNAP. Each is small next to the coverage losses, so they
are described here and left out of the totals.

- **LIHEAP and the utility allowance ("heat and eat").** Before H.R. 1, any SNAP household that got $21 or more in
  LIHEAP energy assistance received Illinois's top utility allowance, which raises SNAP benefits. Since Sept 26, 2025,
  that applies only to households with a member aged 60+ or with a disability (IDHS PM 13-01-08-b). Affected are
  households with no such member that got the top allowance *only* through LIHEAP, i.e. they pay no heating or
  air-conditioning bill themselves. They move to a lower allowance: a benefit cut of up to about $28/month if they
  still pay two or more other utility bills, or about $149/month if they pay only a phone bill (IDHS FY2027 standards
  $565 / $472 / $69; benefits fall 30 cents per $1 of income). Even at 20,000-50,000 Cook households, that is about
  $7-17M a year, roughly 1-3% of the SNAP dollars lost to coverage losses. IDHS does not publish the number of
  affected households. Per-household figures: `output/tables/snap_liheap_cut_per_household.csv`.
- **Internet costs excluded from the utility allowance.** H.R. 1 bars counting internet costs. It is not confirmed
  that Illinois's allowance ever included them, so the effect is likely zero to a few dollars per household.
- **Thrifty Food Plan cost-neutrality.** Limits future increases in benefit levels; no effect assumed within 2026-2028.

## Medicaid work-requirement losses: where the rates come from

**What we use.** For each scenario, the share of Cook ACA adults who lose Medicaid because of the work requirement
(including exempt adults who can't document their exemption) equals the Urban Institute's Illinois estimate for
2028: **18% / 29% / 42%** of ACA adults (our low / mid / high = Urban's high / medium / low "mitigation").
Losses from renewing every 6 months come from the same report: **8% / 15% / 15%**. Urban measures the work-requirement
piece *after* renewals, so the two add without double counting. From these we derive the loss rate among adults
subject to the requirement: about 38% / 58% / 82%. These replace the 19/30/40% in the original plan, which had no
source.

**Why Urban's high-mitigation setting is our low scenario.** Urban's scenarios differ by five choices states make.
Illinois has announced all five, and each matches Urban's most protective setting
(`output/tables/illinois_vs_urban_scenarios.csv`; every quote is checked automatically against the downloaded documents):

| Choice | Urban high / medium / low | Illinois | Source |
|---|---|---|---|
| Months of compliance required | 1 / 3 / 3 | "Illinois has chosen one month." | HFS Module 3, p11 |
| Self-employment | data or self-attestation / no / no | Self-attestation accepted where data can't verify | HFS Module 3, p22 |
| Students identified in data | 50% / 20% / none | National Student Clearinghouse | HFS Module 3, p19 |
| SNAP data match | 95% / 75% / 67% (integrated states) | "HFS and DHS share the same eligibility system"; exemption automatic | HFS FAQ |
| Medical frailty | broad, self-attested ADLs / broad / narrow | Broad, incl. difficulty with daily activities; verification awaits CMS guidance | HFS FAQ |

What Illinois can't choose is how people respond. Urban assumes 65% / 75% / 87% of people who must report manually
don't. That range comes from Arkansas and New Hampshire, where 72% and 82% of those asked to report were
"noncompliant" in the first month, even though more than 95% of Arkansas adults targeted were working or exempt.
So our low scenario means "Illinois as announced, and people respond as well as in Urban's best case". Mid and high mean
people respond as poorly as in past programs.

**Caveats.**
- KFF's table, which Urban used to sort states, lists Illinois's Medicaid system as *not* determining SNAP, but HFS
  says the two share one system. If HFS is right, Urban's Illinois figures assume a weaker SNAP match than Illinois
  has, and true losses could be somewhat lower.
- Urban counts new applicants turned away; we don't model them separately. Applying Urban's share to existing
  enrollees partly stands in for them.
- HFS's own internal estimate (draft, method not published): 165,000-330,000 of ~700,000 Illinois ACA adults lose
  coverage from work requirements, which is 24%-47%. Our mid and high scenarios fall in that range.

**Sources (root documents; those marked * are downloaded to `data/raw/`):**
- \* Buettgens M, Karpman M, Haley JM, Carter J, Kenney GM. *Medicaid Expansion Enrollment Under OBBBA's Work
  Requirements and Redeterminations.* Urban Institute for the Robert Wood Johnson Foundation, March 2026. Table 3
  (p40), Table A.1 (p55), Table A.2 (p57). https://www.rwjf.org/content/dam/farm/reports/reports/2026/rwjf485284
- Urban's evidence, cited as Urban cites it:
  - \* Sommers BD, Goldman AL, Blendon RJ, Orav EJ, Epstein AM. "Medicaid Work Requirements: Results from the First
    Year in Arkansas." *NEJM* 381:1073-82 (2019). doi:10.1056/NEJMsr1901772. (Cited in Urban's text but missing from
    its reference list.)
  - \* Brookings working paper on enrollment effects of an Arkansas-style work requirement (2025), apparently the
    "Fiedler (2025)" Urban cites for re-enrollment (8.4% of removed enrollees return in the first eligible month, 3.4%
    a month after). https://www.brookings.edu/wp-content/uploads/2026/04/ArkansasStyleWorkRequirementEnrollmentEffects-FINAL.pdf
    (Not in Urban's reference list; the author's name is not printed in the extracted text.)
  - Arkansas Department of Human Services, Arkansas Works Section 1115 quarterly reports (2018); Hill I, Burroughs E.
    *Lessons from Launching Medicaid Work Requirements in Arkansas* (Urban, 2019); Hill I, Burroughs E, Adams G.
    *New Hampshire's Experiences with Medicaid Work Requirements* (Urban, 2020); Musumeci M, Rudowitz R, Hall C.
    "An Early Look at Implementation of Medicaid Work Requirements in Arkansas" (KFF, 2018); Wagner J, Schubel J.
    "States' Experiences Confirm Harmful Effects of Medicaid Work Requirements" (CBPP, 2020).
  - \* KFF, "Integration of Medicaid and Non-health Program Eligibility Systems" (as of Jan 2026).
    https://www.kff.org/affordable-care-act/state-indicator/integration-of-medicaid-and-non-health-program-eligibility-systems/
  - Buettgens M, Carter J, Hernandez F. "OBBBA's Six-Month Redetermination Could Reduce Medicaid Expansion Enrollment
    by 2.0 to 3.1 Million in 2028" (Urban, 2026): the method behind Urban's renewal estimates.
- Illinois HFS:
  - \* *HR1 Webinar Series Module 3: Work Requirements* (draft, July 14 2026).
    https://hfs.illinois.gov/content/dam/soi/en/web/hfs/info/fedresctr/hr1mod3wrce.pdf
  - \* FAQ "How will federal changes impact Medicaid". https://hfs.illinois.gov/info/fedresctr/faqshowwillfedchimpactmedicaid.html
  - \* ACA Adult customer notice (Aug 31 2026).
    https://hfs.illinois.gov/content/dam/soi/en/web/hfs/medicalclients/medicaidguide/ACAAdultCustomerNotice083126ToPrint.pdf

## Who is likely to lose both programs (step 6d)

Census ACS 2020-24 microdata (PUMS) for Cook adults in the Medicaid expansion group. Each person is weighted by their
survey weight times their estimated chance of losing both Medicaid and SNAP by December 2028 (from the overlap step:
midpoint of "independent" and "fully correlated" losses). Margins of error use the 80 replicate weights, holding the
chances fixed, so they understate total uncertainty. Excludes the noncitizen cut (about 2,000 people, added separately
in the counts). The survey predates H.R. 1: this describes who is likely to lose both, not people observed losing them.
Output: output/tables/pums_profiles_both.csv (all scenarios, both overlap ends) and pums_profiles_both_wide.csv.

## What the county is doing (step 6c)

Public releases only: Cook County FY2027 budget recommendation (Oct 8, 2026) and preliminary forecast (June 17, 2026),
CCH FY2027 budget presentation (July 31, 2026), the county's $19.9M food and housing investment (Mar 11, 2026), CCH's
Food as Medicine release (Jan 23, 2026) and NACo awards release (Sept 1, 2026). Every number and statement used is
stored with its exact quote in params.yaml (county.response) and checked against the downloaded file on each run.
Comparisons in the article (e.g. $10M to the Food Depository vs. federal SNAP dollars lost) set one-time county money
against our annual estimates; they are scale comparisons, not a forecast of county decisions.
