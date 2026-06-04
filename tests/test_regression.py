"""Regression tests — each locks in a specific failure mode so it can't return.

These guard known model-output failure modes, written proactively to demonstrate
the pattern the role asks for: every bug fixed gets a regression test that names
the failure it guards against.
"""

from doc_intake.schema import ExtractedDoc


def test_amount_with_currency_symbol_and_commas_parses():
    # FAILURE MODE: models return money as a string like "$1,234.56"; a bare
    # float() raises on the "$" and commas. The coercing field_validator handles
    # it, and this test locks that behavior in.
    doc = ExtractedDoc(
        doc_type="invoice", title="X", date="2026-01-01",
        total_amount="$1,234.56",
    )
    assert doc.total_amount == 1234.56


def test_blank_amount_string_becomes_none():
    # FAILURE MODE: a blank amount string "" would crash float(); it should be
    # treated as "no amount present" rather than an error.
    doc = ExtractedDoc(
        doc_type="invoice", title="X", date="2026-01-01", total_amount="",
    )
    assert doc.total_amount is None
