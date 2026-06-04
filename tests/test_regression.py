"""Regression tests — each one locks in a specific bug that was fixed.

The discipline from the role: every bug fixed gets a regression test before the
fix is considered done. Each test below names the bug it guards against.
"""

from doc_intake.schema import ExtractedDoc


def test_amount_with_currency_symbol_and_commas_parses():
    # BUG (2026-06-03): the model returns money as a string like "$1,234.56".
    # A bare float() raised ValueError on the "$" and commas, which failed the
    # entire extraction. Fixed with a coercing field_validator. This locks it.
    doc = ExtractedDoc(
        doc_type="invoice", title="X", date="2026-01-01",
        total_amount="$1,234.56",
    )
    assert doc.total_amount == 1234.56


def test_blank_amount_string_becomes_none():
    # BUG (2026-06-03): a blank amount string "" crashed float(). It should be
    # treated as "no amount present" rather than an error.
    doc = ExtractedDoc(
        doc_type="invoice", title="X", date="2026-01-01", total_amount="",
    )
    assert doc.total_amount is None
