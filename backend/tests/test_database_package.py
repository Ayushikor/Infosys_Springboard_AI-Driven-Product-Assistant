"""Tests for the top-level ``database`` package (schemas, validators, indexes)."""

import os
import sys
import pathlib

import pytest

ROOT = str(pathlib.Path(__file__).resolve().parents[2])
if ROOT not in sys.path:
    sys.path.append(ROOT)

from pymongo.errors import ServerSelectionTimeoutError  # noqa: E402

import database  # noqa: E402
from database import INDEX_SPECS, create_indexes, validate  # noqa: E402
from database.schemas import SCHEMA_MODULES, VALIDATORS  # noqa: E402


# ---- schemas ---------------------------------------------------------------

@pytest.mark.parametrize("module", SCHEMA_MODULES, ids=lambda m: m.COLLECTION)
def test_example_documents_are_valid(module):
    assert validate(module.COLLECTION, module.EXAMPLE) == []


@pytest.mark.parametrize("module", SCHEMA_MODULES, ids=lambda m: m.COLLECTION)
def test_non_object_is_rejected(module):
    assert validate(module.COLLECTION, "nope") == ["document must be an object"]


def test_every_indexed_collection_has_a_schema():
    assert {s["collection"] for s in INDEX_SPECS} <= set(VALIDATORS)


def test_user_rules():
    good = dict(database.schemas.user_schema.EXAMPLE)
    assert validate("users", {**good, "username": "a!"})
    assert validate("users", {**good, "email": "Jane@Example.com"})
    assert validate("users", {**good, "passwordHash": ""})


def test_feedback_follows_normalize_rules():
    good = dict(database.schemas.feedback_schema.EXAMPLE)
    assert validate("feedback", {**good, "sentiment": "angry"})
    assert validate("feedback", {**good, "votes": -1})
    assert validate("feedback", {**good, "message": " "})
    assert validate("feedback", {**good, "createdAt": "yesterday"})


def test_feature_ranges():
    good = dict(database.schemas.feature_schema.EXAMPLE)
    assert validate("features", {**good, "impact": 5})
    assert validate("features", {**good, "confidence": 1.5})
    assert validate("features", {**good, "effort": 0})


def test_roadmap_dates():
    good = dict(database.schemas.roadmap_schema.EXAMPLE)
    assert validate("roadmap", {**good, "startDate": "", "targetDate": ""}) == []
    assert validate("roadmap", {**good, "targetDate": "2026-01-01"})
    assert validate("roadmap", {**good, "startDate": "01/03/2026"})


def test_product_catalog_item_may_omit_user_id():
    doc = dict(database.schemas.product_schema.EXAMPLE)
    assert "userId" not in doc and validate("products", doc) == []


def test_user_state_preferences():
    assert validate("user_state", {"userId": "u"}) == []
    assert validate("user_state", {"userId": "u", "preferences": {"compactTables": "no"}})


def test_unknown_fields_are_allowed():
    doc = {**database.schemas.theme_schema.EXAMPLE, "extra": 1}
    assert validate("themes", doc) == []


# ---- architecture constraints ---------------------------------------------

def test_package_does_not_create_its_own_client():
    base = pathlib.Path(database.__file__).parent
    for path in base.rglob("*.py"):
        assert "MongoClient(" not in path.read_text(), path


def test_package_does_not_import_backend_modules():
    base = pathlib.Path(database.__file__).parent
    for path in base.rglob("*.py"):
        text = path.read_text()
        assert "from db import" not in text and "import backend" not in text, path


# ---- indexes ---------------------------------------------------------------

def test_index_names_are_unique():
    names = [s["name"] for s in INDEX_SPECS]
    assert len(names) == len(set(names))


class _DownCollection:
    def aggregate(self, *_a, **_k):
        raise ServerSelectionTimeoutError("down")

    def create_index(self, *_a, **_k):
        raise ServerSelectionTimeoutError("down")


class _DownDB:
    def __getitem__(self, _name):
        return _DownCollection()


def test_create_indexes_stops_after_first_connection_failure():
    summary = create_indexes(_DownDB())
    assert len(summary["failed"]) == 1
    assert summary["ensured"] == []


@pytest.fixture
def mongo_db():
    mongomock = pytest.importorskip("mongomock")
    return mongomock.MongoClient()["database_package_test"]


def test_create_indexes_is_idempotent(mongo_db):
    first = create_indexes(mongo_db)
    second = create_indexes(mongo_db)
    assert first["failed"] == [] and first["skipped"] == []
    assert second["ensured"] == first["ensured"]
    assert "email_1" not in mongo_db["users"].index_information()
    assert "users_email_unique" in mongo_db["users"].index_information()


def test_unique_index_skipped_when_duplicates_exist(mongo_db):
    mongo_db["users"].insert_many([
        {"id": "usr-1", "email": "a@example.com", "username": "alice"},
        {"id": "usr-2", "email": "a@example.com", "username": "bob"},
    ])
    summary = create_indexes(mongo_db)
    assert "users_email_unique" in summary["skipped"]
    assert "users_id_unique" in summary["ensured"]
    assert mongo_db["users"].count_documents({}) == 2  # data untouched


def test_seeded_theme_ids_do_not_collide_across_users(mongo_db):
    create_indexes(mongo_db)
    mongo_db["themes"].insert_one({"id": "th-ux", "userId": "usr-1"})
    mongo_db["themes"].insert_one({"id": "th-ux", "userId": "usr-2"})
    assert mongo_db["themes"].count_documents({"id": "th-ux"}) == 2
