# Check report

Generated 2026-10-29 18:27

| step | PASS | WARN |
|---|---|---|
| 00b_manifest | 276 | 0 |
| 01a_snap_parse | 170 | 2 |
| 01b_hfs_parse | 17 | 0 |
| 01c_cch_parse | 72 | 0 |
| 01d_geo_acs | 17 | 0 |
| 01e_independent_recheck | 253 | 0 |
| 01f_urban_parse | 10 | 0 |
| 01g_il_vs_urban | 18 | 0 |
| 02_snap_series | 11 | 0 |
| 03_pums_shares | 42 | 0 |
| 03b_profiles | 5 | 1 |
| 04_medicaid | 45 | 0 |
| 05_snap | 51 | 0 |
| 05b_overlap | 14 | 0 |
| 05c_county_pressure | 8 | 0 |
| 06_zip_alloc | 15 | 0 |

## Not passing

- **WARN** `01a_snap_parse` office months contiguous: expected no gaps, got missing [Period('2024-02', 'M')]. 
- **WARN** `01a_snap_parse` Sept 2025 Cook: county PDF vs office table (within 1%): expected 851,244 (rel_tol=0.01), got 881,937. county PDF 881,937 vs office 851,244 (+3.6%); state 1,855,852 vs 1,864,292 (-0.5%). Different definitions (likely county of residence vs. servicing office, or a different count date). The office series is used for the time trend; the gap is reported.
- **WARN** `03b_profiles` PUMAs are clearly Chicago or suburban (none 10-90% Chicago): expected True, got False. mixed PUMAs: {'03109': 0.13, '03164': 0.84}
