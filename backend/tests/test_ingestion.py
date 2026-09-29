import json

import pytest

from app.services.ingestion import parse_upload


SAMPLE_CSV = b"""sender_email,sender_name,subject,body,is_vip
a@example.com,Alice,Payment issue,My card was charged twice,true
b@example.com,Bob,Question,How do I export data?,false
"""


def test_parses_standard_csv():
    tickets = parse_upload("tickets.csv", SAMPLE_CSV)
    assert len(tickets) == 2
    assert tickets[0].sender_email == "a@example.com"
    assert tickets[0].sender_name == "Alice"
    assert tickets[0].is_vip is True
    assert tickets[1].is_vip is False


def test_parses_json_array():
    records = [
        {"sender_email": "c@example.com", "subject": "Hi", "body": "Test body"},
    ]
    tickets = parse_upload("tickets.json", json.dumps(records).encode("utf-8"))
    assert len(tickets) == 1
    assert tickets[0].subject == "Hi"


def test_column_aliases_are_recognized():
    csv_with_aliases = b"from,name,subject,message\na@example.com,Alice,Hi,Test text\n"
    tickets = parse_upload("tickets.csv", csv_with_aliases)
    assert tickets[0].sender_email == "a@example.com"
    assert tickets[0].body == "Test text"


def test_missing_required_column_raises_clear_error():
    bad_csv = b"subject,body\nHi,Test\n"  # missing sender_email
    with pytest.raises(ValueError, match="sender_email"):
        parse_upload("tickets.csv", bad_csv)


def test_new_tickets_default_to_new_status():
    tickets = parse_upload("tickets.csv", SAMPLE_CSV)
    assert all(t.status == "new" for t in tickets)


def test_is_vip_accepts_various_truthy_strings():
    csv_data = b"sender_email,subject,body,is_vip\na@example.com,s,b,YES\n"
    tickets = parse_upload("tickets.csv", csv_data)
    assert tickets[0].is_vip is True
