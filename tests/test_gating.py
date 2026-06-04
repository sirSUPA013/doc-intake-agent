"""Unit tests for the PIN gate and cost guardrails (web/gating.py)."""

import pytest

from web import gating


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(gating, "DEMO_PIN", "secret-pin")
    monkeypatch.setattr(gating, "_SECRET", b"test-secret")
    monkeypatch.setattr(gating, "DAILY_LIVE_CAP", 3)
    gating._counter["date"] = None
    gating._counter["count"] = 0
    yield


def test_pin_ok():
    assert gating.pin_ok("secret-pin")
    assert not gating.pin_ok("wrong")
    assert not gating.pin_ok("")


def test_cookie_roundtrip():
    assert gating.read_cookie(gating.make_cookie(override=False)) == (True, False)
    assert gating.read_cookie(gating.make_cookie(override=True)) == (True, True)


def test_tampered_or_missing_cookie_rejected():
    good = gating.make_cookie(override=True)
    tampered = good[:-1] + ("0" if good[-1] != "0" else "1")
    assert gating.read_cookie(tampered) == (False, False)
    assert gating.read_cookie(None) == (False, False)
    assert gating.read_cookie("garbage") == (False, False)


def test_decide_mode_locked_is_demo():
    assert gating.decide_mode(unlocked=False, override=False) == "demo"


def test_decide_mode_unlocked_under_cap_is_live():
    assert gating.decide_mode(unlocked=True, override=False) == "live"


def test_cap_blocks_live_unless_overridden():
    for _ in range(3):
        gating.record_live_call()
    assert gating.cap_reached()
    assert gating.decide_mode(unlocked=True, override=False) == "demo"
    assert gating.decide_mode(unlocked=True, override=True) == "live"


def test_daily_counter_rolls_on_new_day(monkeypatch):
    gating.record_live_call()
    assert gating.live_used_today() == 1
    monkeypatch.setattr(gating, "_today", lambda: "2999-01-01")
    assert gating.live_used_today() == 0  # new day resets the count
