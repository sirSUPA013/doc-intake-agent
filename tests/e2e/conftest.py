"""Fixture that boots the real FastAPI app in a subprocess for Playwright.

The readiness poll (wait until the server actually answers, with a timeout and an
early-exit check) is deliberate flaky-test hygiene: a naive fixed sleep is the
classic source of an intermittently red E2E test.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server():
    port = _free_port()
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "web.app:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{base_url}/healthz", timeout=1)
            break
        except Exception:
            if proc.poll() is not None:
                raise RuntimeError("uvicorn exited before becoming ready")
            time.sleep(0.3)
    else:
        proc.terminate()
        raise RuntimeError("server did not become ready within 30s")

    yield base_url

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
