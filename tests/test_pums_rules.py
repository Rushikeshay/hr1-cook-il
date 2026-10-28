"""Synthetic households with known answers for the PUMS H.R. 1 rules. Run: python -m pytest tests -q"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lib import pums_rules as R  # noqa: E402

# A baseline adult who is in the Medicaid ACA-adult universe, not exempt, not working.
BASE = dict(AGEP="30", HINS3="2", HINS4="1", POVPIP="80", SSIP="0", PAP="0", DIS="2", SCH="1", FER="2",
            DRAT="b", RACAIAN="0", WKHP="", WKL="3", PERNP="0", ADJINC="1015250", ESR="6", RELSHIPP="20",
            MIL="4", CIT="1")


def build(households, fs=None):
    """households: list of households, each a list of dicts overriding BASE. fs: SNAP flag per household."""
    persons, housing = [], []
    for i, hh in enumerate(households):
        sn = f"H{i}"
        for j, p in enumerate(hh):
            persons.append({**BASE, **p, "SERIALNO": sn, "SPORDER": str(j + 1)})
        housing.append({"SERIALNO": sn, "FS": (fs or {}).get(i, "2")})
    return R.prepare(pd.DataFrame(persons).replace("", None), pd.DataFrame(housing))


def med(households, fs=None, **rules):
    return R.medicaid_flags(build(households, fs), rules)


def first(flags):
    return flags.iloc[0].to_dict()


# ---------------------------------------------------------------- universe
def test_single_30yo_works_10hrs_no_disability_is_subject_and_noncompliant():
    f = first(med([[dict(WKHP="10", WKL="1", ESR="1", PERNP="3000")]]))  # $250/month
    assert f["universe"] and f["subject"] and not f["exempt"]
    assert f["subject_noncompliant_hours"] and f["subject_noncompliant_earnings"] and f["subject_noncompliant_either"]


@pytest.mark.parametrize("override", [
    dict(AGEP="18"), dict(AGEP="65"),            # outside 19-64
    dict(HINS4="2"),                             # no Medicaid
    dict(HINS3="1"),                             # has Medicare
    dict(SSIP="4000"),                           # gets SSI
    dict(POVPIP="139"), dict(POVPIP=""),         # income above limit / N/A
])
def test_outside_universe(override):
    assert not first(med([[override]]))["universe"]


def test_ages_19_and_64_are_in_universe():
    f = med([[dict(AGEP="19")], [dict(AGEP="64")]])
    assert f.universe.all()


def test_household_with_child_under_18_excluded_everyone_in_home():
    f = med([[dict(), dict(AGEP="17", RELSHIPP="25"), dict(AGEP="22", RELSHIPP="25")]])
    assert not f.universe.any()  # parent AND the 22-year-old sibling (household rule)


def test_caretaker_rule_keeps_adult_sibling():
    f = med([[dict(), dict(AGEP="17", RELSHIPP="25"), dict(AGEP="22", RELSHIPP="25")]], child_rule="caretaker")
    assert list(f.universe) == [False, False, True]


def test_child_aged_18_does_not_exclude():
    assert first(med([[dict(), dict(AGEP="18", RELSHIPP="25", HINS4="2")]]))["universe"]


# ---------------------------------------------------------------- exemptions
@pytest.mark.parametrize("override,col", [
    (dict(FER="1"), "ex_pregnant_postpartum"),
    (dict(DIS="1"), "ex_medically_frail_disability"),
    (dict(DRAT="5"), "ex_veteran_disability_rating"),
    (dict(RACAIAN="1"), "ex_american_indian_alaska_native"),
    (dict(SCH="2"), "ex_half_time_student"),
    (dict(PAP="2000", ESR="1", WKHP="10", WKL="1"), "ex_meets_snap_tanf_work_rules"),
])
def test_each_exemption(override, col):
    f = first(med([[override]]))
    assert f["universe"] and f["exempt"] and f[col] and not f["subject"]
    assert not f["subject_noncompliant_either"]


def test_veteran_with_lower_rating_not_exempt():
    assert first(med([[dict(DRAT="3", MIL="2")]]))["subject"]


def test_caregiver_of_disabled_housemate_exempt_but_not_the_disabled_one_by_caregiving():
    f = med([[dict(), dict(AGEP="40", RELSHIPP="21", DIS="1")]])
    assert f.ex_caregiver_disabled_member.tolist() == [True, False]
    assert f.ex_medically_frail_disability.tolist() == [False, True]
    assert f.exempt.all()


def test_pap_without_work_is_not_exempt():
    assert first(med([[dict(PAP="2000")]]))["subject"]


def test_snap_household_meeting_hours_is_exempt_but_snap_alone_is_not():
    f = med([[dict(WKHP="25", WKL="1", ESR="1")], [dict()]], fs={0: "1", 1: "1"})
    assert f.exempt.tolist() == [True, False]


def test_student_as_compliant_instead_of_exempt():
    f = first(med([[dict(SCH="3")]], half_time_student="compliant"))
    assert f["subject"] and not f["exempt"]
    assert not f["subject_noncompliant_hours"] and not f["subject_noncompliant_either"]
    assert f["subject_noncompliant_earnings"]


# ---------------------------------------------------------------- compliance
def test_works_20_hours_compliant_by_hours():
    f = first(med([[dict(WKHP="20", WKL="1", ESR="1", PERNP="0")]]))
    assert f["subject"] and not f["subject_noncompliant_hours"] and not f["subject_noncompliant_either"]
    assert f["subject_noncompliant_earnings"]


def test_hours_without_work_in_past_year_not_compliant():
    assert first(med([[dict(WKHP="40", WKL="2")]]))["subject_noncompliant_hours"]


def test_earnings_threshold_uses_adjinc():
    # $6,900/yr x 1.01525 / 12 = $583.77 -> meets $580; same earnings without the adjustment = $575 -> fails
    ok = first(med([[dict(PERNP="6900", WKHP="10", WKL="1", ESR="1")]]))
    no = first(med([[dict(PERNP="6900", WKHP="10", WKL="1", ESR="1", ADJINC="1000000")]]))
    assert not ok["subject_noncompliant_earnings"] and not ok["subject_noncompliant_either"]
    assert no["subject_noncompliant_earnings"]
    assert ok["subject_noncompliant_hours"]


def test_noncompliant_is_subset_of_subject():
    f = med([[dict(DIS="1")], [dict()], [dict(AGEP="70")]])
    for c in ("hours", "earnings", "either"):
        assert (f[f"subject_noncompliant_{c}"] <= f.subject).all()
    assert (f.subject | f.exempt).equals(f.universe)


# ---------------------------------------------------------------- SNAP time limit
def snap(households, fs):
    return R.snap_flags(build(households, fs))


def test_snap_single_adult_not_working_is_time_limited():
    f = first(snap([[dict(AGEP="45")]], {0: "1"}))
    assert f["on_snap"] and f["time_limited"] and f["time_limited_not_working"]


def test_snap_ages_18_and_64_time_limited_65_not():
    f = snap([[dict(AGEP="18")], [dict(AGEP="64")], [dict(AGEP="65")]], {0: "1", 1: "1", 2: "1"})
    assert f.time_limited.tolist() == [True, True, False]


def test_snap_child_13_exempts_household_child_14_does_not():
    f = snap([[dict(), dict(AGEP="13", RELSHIPP="25")], [dict(), dict(AGEP="14", RELSHIPP="25")]], {0: "1", 1: "1"})
    assert f.time_limited.tolist() == [False, False, True, False]  # 14-year-old is under 18 -> not time-limited


def test_snap_working_20_hours_time_limited_but_meets_rule():
    f = first(snap([[dict(WKHP="20", WKL="1", ESR="1")]], {0: "1"}))
    assert f["time_limited"] and not f["time_limited_not_working"]


def test_snap_not_on_snap_or_group_quarters():
    f = snap([[dict()], [dict(RELSHIPP="38")]], {0: "2", 1: "1"})
    assert not f.on_snap.any()


@pytest.mark.parametrize("override", [dict(DIS="1"), dict(FER="1"), dict(RACAIAN="1"), dict(SCH="2"),
                                      dict(PAP="1000", ESR="1")])
def test_snap_exemptions(override):
    assert not first(snap([[override]], {0: "1"}))["time_limited"]
