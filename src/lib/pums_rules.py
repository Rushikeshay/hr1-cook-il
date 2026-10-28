"""H.R. 1 rules applied to ACS PUMS person records. Every rule here is a PROXY: PUMS has no direct flag
for most exemptions. Codes checked against PUMS_Data_Dictionary_2020-2024.csv. Tested in tests/test_pums_rules.py.

    df = prepare(persons, housing)
    m = medicaid_flags(df, rules)     # universe, exemptions, subject, compliance
    s = snap_flags(df)                # SNAP time-limited adults

Medicaid universe (HFS "ACA adult"): age 19-64, Medicaid/means-tested coverage (HINS4), no Medicare (HINS3),
no SSI, income <= 138% of poverty (POVPIP), no child <18 in the home.
Shares:  (a) subject = in universe and not exempt
         (b) subject and not already compliant (hours, earnings, or either)
"""
import pandas as pd

EMPLOYED = {"1", "2", "4", "5"}            # ESR: civilian/armed forces, at work or with a job
STUDENT = {"2", "3"}                       # SCH: attended public/private school in the last 3 months
CARETAKER_REL = {"20", "21", "22", "23", "24"}  # RELSHIPP: reference person, spouse, unmarried partner
GQ_REL = {"37", "38"}                      # RELSHIPP: group quarters
NUMERIC = ["AGEP", "POVPIP", "SSIP", "PAP", "WKHP", "PERNP", "ADJINC"]

DEFAULT_RULES = dict(poverty_limit_pct=138, child_rule="household", half_time_student="exempt",
                     veteran_rating_code="5", income_test_monthly=580, hours_test_weekly=20)


def rules_from_params(P):
    w, r = P["medicaid"]["work_requirement"], P["medicaid"]["pums_rules"]
    return dict(poverty_limit_pct=r["poverty_limit_pct"]["value"], child_rule=r["child_rule"]["value"],
                half_time_student=r["half_time_student"]["value"],
                veteran_rating_code=str(r["veteran_rating_code"]["value"]),
                income_test_monthly=w["income_test_monthly"]["value"],
                hours_test_weekly=w["hours_test_weekly"]["value"])


def prepare(persons, housing):
    """Typed person records with household SNAP receipt and household-composition features."""
    df = persons.copy()
    for c in NUMERIC:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in set(df.columns) - set(NUMERIC):
        if df[c].dtype == object:
            df[c] = df[c].fillna("b")  # PUMS blank = N/A
    df = df.merge(housing[["SERIALNO", "FS"]].fillna("b"), on="SERIALNO", how="left", validate="m:1")
    df["FS"] = df.FS.fillna("b")
    hh = df.SERIALNO
    dis = df.DIS == "1"
    df["hh_n_u18"] = (df.AGEP < 18).groupby(hh).transform("sum")
    df["hh_n_u14"] = (df.AGEP < 14).groupby(hh).transform("sum")
    df["hh_n_60plus"] = (df.AGEP >= 60).groupby(hh).transform("sum")
    df["hh_n_dis"] = dis.groupby(hh).transform("sum")
    df["other_dis"] = df.hh_n_dis - dis.astype(int)   # someone ELSE in the home has a disability
    df["earn_month"] = df.PERNP.fillna(0) * df.ADJINC / 1e6 / 12  # 2024 dollars
    df["employed"] = df.ESR.isin(EMPLOYED)
    df["in_gq"] = df.RELSHIPP.isin(GQ_REL)
    return df


def meets_hours(df, weekly=20):
    """Usually works >= `weekly` hours and worked in the past 12 months (80 hrs/month proxy)."""
    return (df.WKHP.fillna(0) >= weekly) & (df.WKL == "1")


def medicaid_universe(df, poverty_limit_pct=138, child_rule="household", **_):
    u = (df.AGEP.between(19, 64) & (df.HINS4 == "1") & (df.HINS3 == "2") & (df.SSIP.fillna(0) <= 0))
    if poverty_limit_pct is not None:
        u &= df.POVPIP <= poverty_limit_pct  # NaN (institutional GQ etc.) -> False
    if child_rule == "household":
        u &= df.hh_n_u18 == 0
    elif child_rule == "caretaker":
        u &= ~(df.RELSHIPP.isin(CARETAKER_REL) & (df.hh_n_u18 > 0))
    elif child_rule != "none":
        raise ValueError(f"unknown child_rule {child_rule!r}")
    return u


def medicaid_exemptions(df, half_time_student="exempt", veteran_rating_code="5", hours_test_weekly=20, **_):
    """One boolean column per exemption proxy (a person can have several)."""
    ex = pd.DataFrame(index=df.index)
    ex["pregnant_postpartum"] = df.FER == "1"              # gave birth in past 12 months
    ex["medically_frail_disability"] = df.DIS == "1"
    ex["veteran_disability_rating"] = df.DRAT == veteran_rating_code
    ex["american_indian_alaska_native"] = df.RACAIAN == "1"
    ex["caregiver_disabled_member"] = df.other_dis > 0
    if half_time_student == "exempt":
        ex["half_time_student"] = df.SCH.isin(STUDENT)
    ex["meets_snap_tanf_work_rules"] = (((df.PAP.fillna(0) > 0) & df.employed)
                                        | ((df.FS == "1") & meets_hours(df, hours_test_weekly)))
    return ex


def medicaid_flags(df, rules=None):
    r = {**DEFAULT_RULES, **(rules or {})}
    out = pd.DataFrame(index=df.index)
    out["universe"] = medicaid_universe(df, **r)
    ex = medicaid_exemptions(df, **r)
    out["exempt"] = out.universe & ex.any(axis=1)
    out["subject"] = out.universe & ~out.exempt
    hours = meets_hours(df, r["hours_test_weekly"])
    if r["half_time_student"] == "compliant":
        hours = hours | df.SCH.isin(STUDENT)
    earn = df.earn_month >= r["income_test_monthly"]
    for name, comp in (("hours", hours), ("earnings", earn), ("either", hours | earn)):
        out[f"subject_noncompliant_{name}"] = out.subject & ~comp
    for c in ex.columns:
        out[f"ex_{c}"] = out.universe & ex[c]
    return out


def snap_flags(df, hours_test_weekly=20):
    """SNAP time limit after H.R. 1: ages 18-64, no child <14 in the household, not exempt.
    Exemption proxies: disability (unfit for work), pregnancy, AIAN, caring for a disabled household member,
    half-time student, TANF work rules (PAP>0 and employed)."""
    out = pd.DataFrame(index=df.index)
    out["on_snap"] = (df.FS == "1") & ~df.in_gq
    exempt = ((df.hh_n_u14 > 0) | (df.DIS == "1") | (df.FER == "1") | (df.RACAIAN == "1") | (df.other_dis > 0)
              | df.SCH.isin(STUDENT) | ((df.PAP.fillna(0) > 0) & df.employed))
    out["time_limited"] = out.on_snap & df.AGEP.between(18, 64) & ~exempt
    out["time_limited_not_working"] = out.time_limited & ~meets_hours(df, hours_test_weekly)
    return out
