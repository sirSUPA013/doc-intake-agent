"""End-to-end UI test with Playwright — a real browser driving the real app.

Run with:  pytest -m e2e
(Excluded from the default suite so the fast unit/integration tests stay fast.)
"""

import pytest

pytestmark = pytest.mark.e2e


def test_extract_flow_in_browser(live_server, page):
    page.goto(live_server)
    page.fill("[data-testid=input]", "ACME Corp  Invoice #42  Total due: $1,250.00")
    page.click("[data-testid=submit]")

    page.wait_for_selector("[data-testid=result]")
    assert page.inner_text("[data-testid=status]") == "done"
    assert "invoice" in page.inner_text("[data-testid=json]")
    assert page.inner_text("[data-testid=summary]").strip() != ""
