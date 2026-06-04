"""PIN gate + cost guardrails for live mode.

Default is demo mode (free, scripted). Entering the PIN unlocks live Claude for
the session. A daily cap on live calls is the backstop so a leaked link can't run
up a bill; checking "override" alongside the PIN lets you bypass the cap when you
genuinely need to (e.g. mid-interview). This is a light gate appropriate for a
public demo, not real authentication.

The daily counter is in-memory, so the Cloud Run service is pinned to a single
instance (--max-instances=1) to keep the count honest. See plans/live-demo-deploy.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
import os

DEMO_PIN = os.environ.get("DEMO_PIN", "")
DAILY_LIVE_CAP = int(os.environ.get("DAILY_LIVE_CAP", "50"))
MAX_INPUT_BYTES = int(os.environ.get("MAX_INPUT_BYTES", "20000"))
# Falls back to the PIN so signed cookies survive restarts even if SESSION_SECRET
# isn't set; set SESSION_SECRET in production for a key independent of the PIN.
_SECRET = (os.environ.get("SESSION_SECRET") or DEMO_PIN or "dev-secret").encode()

COOKIE_NAME = "live_session"

# In-memory daily counter (single-instance — see module docstring).
_counter: dict = {"date": None, "count": 0}


def _today() -> str:
    return datetime.date.today().isoformat()


def _roll_day() -> None:
    if _counter["date"] != _today():
        _counter["date"] = _today()
        _counter["count"] = 0


def live_used_today() -> int:
    _roll_day()
    return _counter["count"]


def cap_reached() -> bool:
    return live_used_today() >= DAILY_LIVE_CAP


def record_live_call() -> None:
    _roll_day()
    _counter["count"] += 1


def _sign(payload: str) -> str:
    mac = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{mac}"


def make_cookie(override: bool) -> str:
    return _sign("override" if override else "live")


def read_cookie(raw: str | None) -> tuple[bool, bool]:
    """Verify a cookie value; return (unlocked, override)."""
    if not raw or "." not in raw:
        return (False, False)
    payload, _, mac = raw.rpartition(".")
    expected = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac, expected):
        return (False, False)
    if payload == "override":
        return (True, True)
    if payload == "live":
        return (True, False)
    return (False, False)


def pin_ok(pin: str) -> bool:
    """Constant-time PIN check. An empty configured PIN disables live mode."""
    return bool(DEMO_PIN) and hmac.compare_digest(pin or "", DEMO_PIN)


def decide_mode(unlocked: bool, override: bool) -> str:
    """The mode a request runs in, before checking key availability."""
    if not unlocked:
        return "demo"
    if override:
        return "live"
    return "demo" if cap_reached() else "live"
