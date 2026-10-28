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
