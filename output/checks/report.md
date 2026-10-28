# Check report

Generated 2026-10-28 10:05

| step | PASS | WARN |
|---|---|---|
| 00b_manifest | 219 | 0 |
| 01a_snap_parse | 170 | 2 |
| 01b_hfs_parse | 17 | 0 |
| 01c_cch_parse | 72 | 0 |
| 01d_geo_acs | 17 | 0 |

## Not passing

- **WARN** `01a_snap_parse` office months contiguous: expected no gaps, got missing [Period('2024-02', 'M')]. nan
- **WARN** `01a_snap_parse` Sept 2025 Cook: county PDF vs office table (within 1%): expected 851,244 (rel_tol=0.01), got 881,937. county PDF 881,937 vs office 851,244 (+3.6%); state 1,855,852 vs 1,864,292 (-0.5%). Different definitions (likely county of residence vs. servicing office, or a different count date). The office series is used for the time trend; the gap is reported.
