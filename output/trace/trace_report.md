# Tracer report

Each tracer unit's value at every pipeline stage.

## month:2026-05

| step | stage | value | note |
|---|---|---|---|
| 01a_snap_parse | Cook SNAP persons (IDHS office table) | 707068 | idhs/offices/snap_offices_2026_05.html table row 55 |
| 01a_snap_parse | Cook SNAP households (IDHS office table) | 404720 | idhs/offices/snap_offices_2026_05.html table row 55 |
| 02_snap_series | observed change vs prior month | -45429 | IDHS office table |
| 02_snap_series | excess change beyond mid trend | -43420 | observed - trend change |
| 05_snap | mid: people off SNAP (residence) | 128190 | wave 1 stock |

## zip:60623

| step | stage | value | note |
|---|---|---|---|
| 01b_hfs_parse | HFS ACA adults FY2025 | 9179 | hfs/fy25_enrollment_by_zip.pdf page 10 |
| 01b_hfs_parse | HFS total comprehensive FY2025 | 42645 | hfs/fy25_enrollment_by_zip.pdf page 10 |
| 01d_geo_acs | cook_share | 1.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | region | Chicago | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | pop | 81277.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | snap_hh | 8113.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | mcd_19_64 | 13315.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | hfs_aca_cook | 9179.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 06_zip_alloc | mid mcd_people_off_dec_2028 | 4243 | Chicago; border=False |
| 06_zip_alloc | mid snap_people_off_dec_2028 | 5594 | Chicago; border=False |
| 06_zip_alloc | mid mcd_federal_usd_2028 | 34653860 | Chicago; border=False |
| 06_zip_alloc | mid snap_federal_usd_2028 | 13090763 | Chicago; border=False |

## zip:60426

| step | stage | value | note |
|---|---|---|---|
| 01b_hfs_parse | HFS ACA adults FY2025 | 3334 | hfs/fy25_enrollment_by_zip.pdf page 6 |
| 01b_hfs_parse | HFS total comprehensive FY2025 | 12945 | hfs/fy25_enrollment_by_zip.pdf page 6 |
| 01d_geo_acs | cook_share | 1.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | region | suburban Cook | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | pop | 23906.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | snap_hh | 3339.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | mcd_19_64 | 5375.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 01d_geo_acs | hfs_aca_cook | 3334.0 | ACS 2020-24 / tract-weighted Cook share / HFS FY2025 |
| 06_zip_alloc | mid mcd_people_off_dec_2028 | 1541 | suburban Cook; border=False |
| 06_zip_alloc | mid snap_people_off_dec_2028 | 2302 | suburban Cook; border=False |
| 06_zip_alloc | mid mcd_federal_usd_2028 | 12586989 | suburban Cook; border=False |
| 06_zip_alloc | mid snap_federal_usd_2028 | 5387657 | suburban Cook; border=False |

## pums:2020HU0051747-01

| step | stage | value | note |
|---|---|---|---|
| 03_pums_shares | person | age 56, HINS4 1, POVPIP 99.0, DIS 2, WKHP 40.0 | weight 5 |
| 03_pums_shares | medicaid status | subject, compliant | headline rules |
| 03_pums_shares | snap status | not on SNAP | nan |

## pums:2020HU0051747-02

| step | stage | value | note |
|---|---|---|---|
| 03_pums_shares | person | age 50, HINS4 1, POVPIP 99.0, DIS 2, WKHP nan | weight 7 |
| 03_pums_shares | medicaid status | subject, not compliant | headline rules |
| 03_pums_shares | snap status | not on SNAP | nan |

## pums:2020HU0051747-03

| step | stage | value | note |
|---|---|---|---|
| 03_pums_shares | person | age 21, HINS4 1, POVPIP 99.0, DIS 2, WKHP 25.0 | weight 7 |
| 03_pums_shares | medicaid status | subject, compliant | headline rules |
| 03_pums_shares | snap status | not on SNAP | nan |

## medicaid_month:2026-10

| step | stage | value | note |
|---|---|---|---|
| 04_medicaid | mid: people off coverage | 5577 | cumulative, all components |

## medicaid_month:2027-04

| step | stage | value | note |
|---|---|---|---|
| 04_medicaid | mid: people off coverage | 14379 | cumulative, all components |

## medicaid_month:2027-12

| step | stage | value | note |
|---|---|---|---|
| 04_medicaid | mid: people off coverage | 98449 | cumulative, all components |

## medicaid_month:2028-12

| step | stage | value | note |
|---|---|---|---|
| 04_medicaid | mid: people off coverage | 165827 | cumulative, all components |

## office:COOK COUNTY

| step | stage | value | note |
|---|---|---|---|
| 05_snap | mid: projected Cook SNAP persons Dec 2028 | 625531 | residence basis |
