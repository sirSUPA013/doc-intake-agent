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
    # case-insensitive: the badge is styled text-transform:uppercase
    assert page.inner_text("[data-testid=status]").strip().lower() == "done"
    # 'invoice' shows in the visible result panel (the raw JSON is collapsed)
    assert "invoice" in page.inner_text("[data-testid=result]").lower()
    assert page.inner_text("[data-testid=summary]").strip() != ""
