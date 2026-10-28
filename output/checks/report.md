# Check report

Generated 2026-10-28 15:43

| step | PASS | WARN |
|---|---|---|
| 00b_manifest | 237 | 0 |
| 01a_snap_parse | 170 | 2 |
| 01b_hfs_parse | 17 | 0 |
| 01c_cch_parse | 72 | 0 |
| 01d_geo_acs | 17 | 0 |
| 01e_independent_recheck | 253 | 0 |
| 01f_urban_parse | 10 | 0 |
| 02_snap_series | 11 | 0 |
| 03_pums_shares | 42 | 0 |
| 04_medicaid | 39 | 1 |

## Not passing

- **WARN** `01a_snap_parse` office months contiguous: expected no gaps, got missing [Period('2024-02', 'M')]. 
- **WARN** `01a_snap_parse` Sept 2025 Cook: county PDF vs office table (within 1%): expected 851,244 (rel_tol=0.01), got 881,937. county PDF 881,937 vs office 851,244 (+3.6%); state 1,855,852 vs 1,864,292 (-0.5%). Different definitions (likely county of residence vs. servicing office, or a different count date). The office series is used for the time trend; the gap is reported.
- **WARN** `04_medicaid` ours (mid) within Urban Illinois range 26%-57% of enrollees (2028, excl. noncitizens): expected [0.2600, 0.5700], got 0.2547. informational: Urban includes denied new applicants and has the full renewal effect all year
