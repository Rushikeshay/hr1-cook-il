"""Tests for the verification helpers. Run: python -m pytest tests -q"""
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lib import checks, ledger  # noqa: E402


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    """Point results/ledger files at a temp dir so tests never touch real outputs."""
    monkeypatch.setattr(checks, "RESULTS", tmp_path / "results.csv")
    monkeypatch.setattr(checks, "CHECKS", tmp_path)
    monkeypatch.setattr(ledger, "LEDGER", tmp_path / "ledger.csv")


def test_checks_pass_and_fail():
    ck = checks.Checks("t1")
    assert ck.equal("eq", 5, 5)
    assert not ck.close("close", 101, 100, rel_tol=0.005)
    assert ck.close("close ok", 100.4, 100, rel_tol=0.005)
    assert not ck.between("between", 2, 0, 1, soft=True)  # soft -> WARN, not fail
    with pytest.raises(checks.CheckFailed):
        ck.finish()
    res = pd.read_csv(checks.RESULTS)
    assert list(res.status) == ["PASS", "FAIL", "PASS", "WARN"]


def test_table_checks():
    ck = checks.Checks("t2")
    df = pd.DataFrame({"k": [1, 1, 2], "v": [1.0, None, -3]})
    assert not ck.no_nulls("nulls", df)
    assert not ck.unique("unique", df, ["k"])
    assert not ck.non_negative("neg", df.v)
    assert not ck.months_contiguous("gaps", ["2026-01", "2026-03"])
    assert ck.months_contiguous("no gaps", ["2026-01", "2026-02"])
    assert ck.ordered("order", 1, 2, 3) and not ck.ordered("bad order", 3, 2, 1)


def test_ledger_rules_and_lineage():
    led = ledger.Ledger("t")
    a = led.observed("a", 100, "people", source="test source")
    b = led.assumed("b", 0.3, "share", source="test")
    led.derived("c", a * b, "people", formula="a * b", inputs=["a", "b"])
    with pytest.raises(ValueError):
        led.derived("d", 1, "x", formula="", inputs=[])           # derived needs inputs
    with pytest.raises(KeyError):
        led.derived("e", 1, "x", formula="z", inputs=["zzz"])     # inputs must exist
    with pytest.raises(ValueError):
        led.observed("f", 1, "x", source="")                       # observed needs source
    with pytest.raises(ValueError):
        led.observed("Bad Id", 1, "x", source="s")
    led.save()
    df = ledger.load().set_index("id")
    assert df.loc["c", "value"] == 30 and df.loc["c", "inputs"] == "a;b"


def test_ledger_from_params_keeps_status_and_scenario_source():
    led = ledger.Ledger("t")
    v = led.from_params("base", "medicaid.baseline_aca_adults", "people")
    assert v == 364204 and led.rows["base"]["label"] == "observed"
    r = led.from_params("rate_mid", "medicaid.loss_rate_subject", "share", scenario="mid")
    assert r == 0.30 and led.rows["rate_mid"]["label"] == "assumed"
