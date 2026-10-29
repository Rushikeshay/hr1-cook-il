"""Step 0: download every raw input into data/raw/. Re-running skips files already present.

Run: python src/00_fetch.py [--force]
"""
import re
import sys
import time
from pathlib import Path

import truststore

truststore.inject_into_ssl()  # use the Windows certificate store (needed behind corporate TLS inspection)

import pandas as pd
import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
P = yaml.safe_load((ROOT / "params.yaml").read_text())
FORCE = "--force" in sys.argv

# IDHS blocks requests without a browser user agent.
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
IDHS = "https://www.dhs.state.il.us/page.aspx?item="

STATE = P["geography"]["state_fips"]
ACS_YEAR = P["geography"]["acs_year"]
PUMS_YEAR = P["geography"]["pums_year"]

FILES = {
    # HFS Medicaid
    "hfs/cook_enrollment.html": "https://hfs.illinois.gov/info/factsfigures/program-enrollment/cook.html",
    "hfs/fy25_enrollment_by_zip.pdf": "https://hfs.illinois.gov/content/dam/soi/en/web/hfs/sitecollectiondocuments/fy25enrollmentbyzipcode.pdf",
    # Cook County Health
    "cch/prelim_fy27_cch_budget.pdf": "https://cookcountyhealth.org/wp-content/uploads/Prelim-FY27-CCH-Budget-Presentation-Final.pdf",
    # IDHS SNAP county counts, Sept 2025
    "idhs/snap_county_2025_09.pdf": "https://www.dhs.state.il.us/OneNetLibrary/27897/documents/SNAP/SEPTEMBER%2025%20SNAP%20Individual%20Counts%20by%20Counties1.pdf",
    # Urban Institute for RWJF (Buettgens et al., Mar 2026): state 2028 Medicaid expansion losses (triangulation)
    "rwjf/urban_medicaid_work_req_2028.pdf": "https://www.rwjf.org/content/dam/farm/reports/reports/2026/rwjf485284",
    # IDHS SNAP utility standards: Oct 2025 (MR #25.33) and current manual chart (WAG 25-03-02 (1))
    "idhs/mr_25_33_utility_standards_2025_10.html": "https://www.dhs.state.il.us/page.aspx?item=171481",
    "idhs/wag_25_03_02_snap_standards.html": "https://www.dhs.state.il.us/page.aspx?item=21738",
    "idhs/pm_13_01_08_b_utility_allowance.html": "https://www.dhs.state.il.us/page.aspx?item=16169",
    "idhs/pm_13_01_08_excess_shelter.html": "https://www.dhs.state.il.us/page.aspx?item=16164",
    # Illinois HFS work-requirement implementation documents (for mapping to Urban scenarios)
    "hfs/aca_adult_customer_notice_2026_08.pdf": "https://hfs.illinois.gov/content/dam/soi/en/web/hfs/medicalclients/medicaidguide/ACAAdultCustomerNotice083126ToPrint.pdf",
    "hfs/hr1_module3_work_requirements.pdf": "https://hfs.illinois.gov/content/dam/soi/en/web/hfs/info/fedresctr/hr1mod3wrce.pdf",
    "hfs/hr1_phase2_toolkit.pdf": "https://hfs.illinois.gov/content/dam/soi/en/web/hfs/info/fedresctr/englishhr1phase2toolkit.pdf",
    "hfs/faq_how_will_fed_changes_impact_medicaid.html": "https://hfs.illinois.gov/info/fedresctr/faqshowwillfedchimpactmedicaid.html",
    "kff/integration_medicaid_nonhealth_eligibility_systems.html": "https://www.kff.org/affordable-care-act/state-indicator/integration-of-medicaid-and-non-health-program-eligibility-systems/",
    # Root sources behind Urban's work-requirement assumptions (Arkansas evidence)
    "evidence/brookings_arkansas_style_work_requirement_2025.pdf": "https://www.brookings.edu/wp-content/uploads/2026/04/ArkansasStyleWorkRequirementEnrollmentEffects-FINAL.pdf",
    "evidence/usda_ers_err265_snap_multiplier_2019.pdf": "https://ers.usda.gov/sites/default/files/_laserfiche/publications/93529/ERR-265.pdf?v=70863",
    "cook/fy2027_preliminary_budget_forecast_release.html": "https://www.cookcountyil.gov/news/cook-county-board-president-toni-preckwinkle-releases-fy2027-preliminary-budget-forecast",
    "evidence/sommers_2019_nejm_arkansas.pdf": "https://digitalgovernmenthub.org/wp-content/uploads/2024/12/NEJMsr1901772.pdf",
    # Geography
    "geo/cb_2020_us_zcta520_500k.zip": "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_zcta520_500k.zip",
    "geo/cb_2024_us_county_500k.zip": "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_us_county_500k.zip",
    "geo/cb_2024_17_place_500k.zip": "https://www2.census.gov/geo/tiger/GENZ2024/shp/cb_2024_17_place_500k.zip",
    "geo/tab20_zcta520_county20_natl.txt": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt",
    "geo/tab20_zcta520_tract20_natl.txt": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_tract20_natl.txt",
    "geo/2020_Census_Tract_to_2020_PUMA.txt": "https://www2.census.gov/geo/docs/maps-data/data/rel2020/2020_Census_Tract_to_2020_PUMA.txt",
}

# IDHS "SNAP Data YYYY" index pages; monthly servicing-office pages are linked from them.
SNAP_INDEX = {2024: 164509, 2025: 171902, 2026: 177664}

PUMS_VARS = [  # person file
    "SERIALNO", "SPORDER", "PWGTP", "ADJINC", "AGEP", "RELSHIPP", "HINS3", "HINS4", "POVPIP",
    "SSIP", "PAP", "DIS", "SCH", "SCHG", "FER", "MIL", "DRAT", "RACAIAN", "WKHP", "WKL",
    "PERNP", "ESR", "CIT",
    "SEX", "HISP", "RAC1P", "SCHL", "ENG", "LANX",  # for the "who is at risk" profiles (step 4b)
] + [f"PWGTP{i}" for i in range(1, 81)]  # replicate weights, for standard errors
PUMS_H_VARS = ["SERIALNO", "WGTP", "NP", "TYPEHUGQ", "FS"] + [f"WGTP{i}" for i in range(1, 81)]  # housing file


def get(url, **kw):
    for attempt in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=120, **kw)
            r.raise_for_status()
            return r
        except requests.RequestException as e:
            if attempt == 3:
                raise
            print(f"  retry {attempt + 1}: {e}")
            time.sleep(3 * (attempt + 1))


SOURCES = {}  # relative path -> where it came from; written to data/raw/_sources.json


def save(rel, url):
    SOURCES[rel] = url
    out = RAW / rel
    if out.exists() and not FORCE:
        return out
    out.parent.mkdir(parents=True, exist_ok=True)
    print(f"GET {url}")
    out.write_bytes(get(url).content)
    return out


def fetch_snap_offices():
    """Save every monthly 'SNAP Data by Servicing Office' page for the indexed years."""
    month_re = re.compile(r'href="\?item=(\d+)">\s*(\w+) (\d{4}) - SNAP Data by Servicing Office', re.I)
    found = []
    for year, item in SNAP_INDEX.items():
        idx = save(f"idhs/index_{year}.html", IDHS + str(item))
        for it, mon, yr in month_re.findall(idx.read_text(encoding="utf-8", errors="replace")):
            m = pd.to_datetime(f"{mon} 1 {yr}").month
            save(f"idhs/offices/snap_offices_{yr}_{m:02d}.html", IDHS + it)
            found.append(f"{yr}-{m:02d}")
    print(f"IDHS servicing-office months: {sorted(found)[0]} .. {sorted(found)[-1]} ({len(found)})")
    if not found:
        print("!! No IDHS monthly pages found. Save them manually into data/raw/idhs/offices/")


def census_key():
    """Census API key from env var CENSUS_API_KEY, else from CENSUS_API_KEY=... in ./.env."""
    import os
    key = os.environ.get("CENSUS_API_KEY")
    env = ROOT / ".env"
    if not key and env.exists():
        for line in env.read_text().splitlines():
            name, _, value = line.partition("=")
            if name.strip() == "CENSUS_API_KEY":
                key = value.strip().strip('"').strip("'")
    return key or None


def census(url, params):
    key = census_key()
    if not key:
        raise SystemExit("Census API needs a free key: https://api.census.gov/data/key_signup.html\n"
                         "Add CENSUS_API_KEY=yourkey to .env (project root).")
    r = get(url, params={**params, "key": key})
    rows = r.json()
    return pd.DataFrame(rows[1:], columns=rows[0])


def fetch_acs_zcta():
    out = RAW / f"acs/acs5_{ACS_YEAR}_zcta.csv"
    SOURCES[f"acs/acs5_{ACS_YEAR}_zcta.csv"] = (f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5 "
                                               "groups B01003,B22003,C27007 for all ZCTAs")
    if out.exists() and not FORCE:
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    groups = ["B01003", "B22003", "C27007"]
    frames = []
    for g in groups:
        print(f"ACS {ACS_YEAR} ZCTA group {g}")
        df = census(f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5",
                    {"get": f"NAME,group({g})", "for": "zip code tabulation area:*"})
        keep = [c for c in df.columns if c.endswith("E") and c.startswith(g)]
        frames.append(df.set_index("zip code tabulation area")[keep])
    pd.concat(frames, axis=1).rename_axis("zcta").to_csv(out)


def fetch_acs_county():
    """County-level citizenship (B05001) and SNAP (B22003) for Cook vs. Illinois shares."""
    out = RAW / f"acs/acs5_{ACS_YEAR}_il_counties.csv"
    SOURCES[f"acs/acs5_{ACS_YEAR}_il_counties.csv"] = (f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5 "
                                                      "groups B05001,B22003,B01003 for Illinois counties")
    if out.exists() and not FORCE:
        return
    frames = []
    for g in ["B05001", "B22003", "B01003"]:
        df = census(f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5",
                    {"get": f"NAME,group({g})", "for": "county:*", "in": f"state:{STATE}"})
        keep = [c for c in df.columns if c.endswith("E") and c.startswith(g)]
        frames.append(df.set_index("county")[keep])
    pd.concat(frames, axis=1).to_csv(out)


def fetch_acs_tracts():
    """Tract population (B01003) for Illinois: population weights for zips crossing the Cook line."""
    rel = f"acs/acs5_{ACS_YEAR}_il_tracts.csv"
    SOURCES[rel] = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5 B01003_001E for Illinois tracts"
    out = RAW / rel
    if out.exists() and not FORCE:
        return
    df = census(f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5",
                {"get": "B01003_001E", "for": "tract:*", "in": f"state:{STATE} county:*"})
    df.to_csv(out, index=False)


def fetch_pums():
    """Illinois 5-year PUMS person + housing files (bulk CSV, no API key), cut to Cook County PUMAs.
    Delete the *_cook.csv files to re-cut after changing PUMS_VARS / PUMS_H_VARS."""
    base = f"https://www2.census.gov/programs-surveys/acs/data/pums/{PUMS_YEAR}/5-Year"
    yrs = f"{PUMS_YEAR - 4}-{PUMS_YEAR}"
    save(f"pums/PUMS_Data_Dictionary_{yrs}.csv",
         f"https://www2.census.gov/programs-surveys/acs/tech_docs/pums/data_dict/PUMS_Data_Dictionary_{yrs}.csv")
    rel = pd.read_csv(RAW / "geo/2020_Census_Tract_to_2020_PUMA.txt", dtype=str)
    rel.columns = [c.strip().lstrip("﻿") for c in rel.columns]
    cook = set(rel.loc[(rel.STATEFP == STATE) & (rel.COUNTYFP == P["geography"]["county_fips"]), "PUMA5CE"])
    import zipfile
    for kind, letter, cols in (("", "p", PUMS_VARS), ("_housing", "h", PUMS_H_VARS)):
        out_rel = f"pums/pums_{PUMS_YEAR}_5yr{kind}_cook.csv"
        zip_rel = f"pums/csv_{letter}il_{PUMS_YEAR}_5yr.zip"
        SOURCES[out_rel] = f"subset of {zip_rel} to Cook PUMAs"
        SOURCES[zip_rel] = f"{base}/csv_{letter}il.zip"
        if (RAW / out_rel).exists() and not FORCE:
            continue
        z = save(zip_rel, f"{base}/csv_{letter}il.zip")
        with zipfile.ZipFile(z) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(name) as f:
                df = pd.read_csv(f, dtype=str, usecols=lambda c: c in cols + ["PUMA", "ST"])
        missing = set(cols) - set(df.columns)
        if missing:
            raise SystemExit(f"PUMS {letter} file is missing columns {sorted(missing)}")
        df = df[df.PUMA.isin(cook)]
        print(f"PUMS {letter}: Cook PUMAs {len(cook)}, records {len(df):,}")
        df.to_csv(RAW / out_rel, index=False)


def fetch_acs_cook_insurance():
    """Published Cook County C27007 (Medicaid/means-tested coverage by age): anchor for PUMS weighted totals."""
    rel = f"acs/acs5_{ACS_YEAR}_cook_c27007.csv"
    SOURCES[rel] = f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5 group C27007 for Cook County"
    if (RAW / rel).exists() and not FORCE:
        return
    df = census(f"https://api.census.gov/data/{ACS_YEAR}/acs/acs5",
                {"get": "NAME,group(C27007)", "for": f"county:{P['geography']['county_fips']}", "in": f"state:{STATE}"})
    keep = [c for c in df.columns if c.startswith("C27007") and c.endswith("E")]
    df[["NAME"] + keep].to_csv(RAW / rel, index=False)


if __name__ == "__main__":
    for rel, url in FILES.items():
        save(rel, url)
    fetch_snap_offices()
    fetch_pums()
    if census_key():
        fetch_acs_zcta()
        fetch_acs_county()
        fetch_acs_tracts()
        fetch_acs_cook_insurance()
    else:
        print("!! Skipped ACS ZCTA/county tables: no Census API key "
              "(https://api.census.gov/data/key_signup.html -> CENSUS_API_KEY in .env)")
    import json
    sf = RAW / "_sources.json"
    old = json.loads(sf.read_text()) if sf.exists() else {}
    sf.write_text(json.dumps({**old, **SOURCES}, indent=1, sort_keys=True))
    print("Done. Files in", RAW)
