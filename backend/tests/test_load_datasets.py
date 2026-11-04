"""Tests for scripts/load_datasets.py (uses mongomock, no live database)."""

import os
import sys

import mongomock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts import load_datasets  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    database = mongomock.MongoClient()["loader_test"]
    database["users"].insert_one({"id": "usr-1", "email": "demo@example.com"})
    monkeypatch.setattr(load_datasets, "get_db", lambda: database)
    return database


def test_loads_all_300_records_for_the_user(db):
    result = load_datasets.run("Demo@Example.com")
    assert result["added"] == 300 and result["skipped"] == 0
    docs = list(db["feedback"].find({"userId": "usr-1"}))
    assert len(docs) == 300
    assert {d["dataset"] for d in docs} == {"customer_feedback", "user_reviews", "support_tickets"}


def test_documents_match_the_backend_feedback_shape(db):
    load_datasets.run("demo@example.com")
    doc = db["feedback"].find_one({"id": "REV-001"})
    assert doc["title"] and doc["message"] and doc["source"]
    assert doc["sentiment"] == "neutral" and doc["theme"] == "Uncategorized"  # unanalysed on purpose
    assert doc["createdAt"].endswith("Z") and doc["votes"] == 0
    assert len(doc["title"]) <= 83


def test_second_run_is_idempotent(db):
    load_datasets.run("demo@example.com")
    again = load_datasets.run("demo@example.com")
    assert again["added"] == 0 and again["skipped"] == 300
    assert db["feedback"].count_documents({}) == 300


def test_dry_run_writes_nothing(db):
    result = load_datasets.run("demo@example.com", dry_run=True)
    assert result["added"] == 300 and db["feedback"].count_documents({}) == 0


def test_reset_only_removes_sample_records(db):
    db["feedback"].insert_one({"id": "fb-abc123", "userId": "usr-1", "title": "mine", "message": "mine"})
    load_datasets.run("demo@example.com")
    result = load_datasets.run("demo@example.com", reset=True)
    assert result["removed"] == 300 and result["added"] == 300
    assert db["feedback"].find_one({"id": "fb-abc123"})


def test_unknown_user_gives_a_clear_error(db):
    with pytest.raises(SystemExit) as err:
        load_datasets.run("nobody@example.com")
    assert "Register in the app first" in str(err.value)


def test_derive_title_shortens_at_word_boundary():
    title = load_datasets.derive_title("word " * 40)
    assert title.endswith("...") and len(title) <= 83