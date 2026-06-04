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


def test_note_without_date_or_title_validates():
    # FAILURE MODE (found 2026-06-04 testing the live demo): freeform handwritten
    # notes have no date or title, the model returns null for them, and the schema
    # rejected it because date/title were required — so every note failed. They're
    # now nullable; only doc_type is required.
    doc = ExtractedDoc(doc_type="note", title=None, date=None, entities=["Mom", "Dave"])
    assert doc.doc_type == "note"
    assert doc.date is None
    assert doc.title is None


def test_key_details_and_transcription_round_trip():
    # FAILURE MODE (found 2026-06-04): a handwritten contact list returned the
    # names but DROPPED the phone numbers, addresses, and the note's text — the
    # 5-field schema had nowhere to put them. transcription + key_details capture
    # everything; this locks that they parse and round-trip.
    doc = ExtractedDoc(
        doc_type="contact list",
        transcription="Tom Casper 502-485-0927\nKaty Casper 502-592-1221",
        key_details=[{"label": "Tom Casper", "value": "502-485-0927"},
                     {"label": "Katy Casper", "value": "502-592-1221"}],
    )
    dumped = doc.model_dump()
    assert dumped["transcription"].startswith("Tom Casper")
    assert dumped["key_details"][0] == {"label": "Tom Casper", "value": "502-485-0927"}


def test_blank_amount_string_becomes_none():
    # FAILURE MODE: a blank amount string "" would crash float(); it should be
    # treated as "no amount present" rather than an error.
    doc = ExtractedDoc(
        doc_type="invoice", title="X", date="2026-01-01", total_amount="",
    )
    assert doc.total_amount is None
