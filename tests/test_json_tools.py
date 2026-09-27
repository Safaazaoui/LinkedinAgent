import pytest

from app.services.json_tools import extract_json


def test_extracts_direct_json():
    assert extract_json('{"stories": []}') == {"stories": []}


def test_extracts_fenced_json():
    assert extract_json('```json\n{"approved": true}\n```') == {
        "approved": True
    }


def test_rejects_non_json():
    with pytest.raises(ValueError):
        extract_json("No structured result was returned.")
