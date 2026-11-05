
import json

import pytest

from app.services.dataset_loader import (
    DATASET_FILES,
    DEFAULT_DATASETS_DIR,
    DatasetLoadError,
    load_feedback_dataset,
)


def create_record(
    feedback_id="FB-001",
    raw_text="The application is loading slowly.",
):
    return {
        "feedback_id": feedback_id,
        "source_channel": "Customer Feedback",
        "raw_text": raw_text,
        "timestamp": "2026-10-05T10:00:00Z",
    }


def write_dataset(directory, filename, records):
    path = directory / filename

    with path.open("w", encoding="utf-8") as file:
        json.dump(records, file)


def create_three_datasets(directory):
    """Create one record in each dataset for testing."""

    write_dataset(
        directory,
        DATASET_FILES["customer_feedback"],
        [create_record("FB-001")],
    )

    write_dataset(
        directory,
        DATASET_FILES["user_reviews"],
        [create_record("REV-001", "The interface is confusing.")],
    )

    write_dataset(
        directory,
        DATASET_FILES["support_tickets"],
        [create_record("TKT-001", "The application crashes.")],
    )


def test_loads_all_three_datasets(tmp_path):
    create_three_datasets(tmp_path)

    records = load_feedback_dataset(tmp_path)

    assert len(records) == 3

    assert {
        record["dataset"] for record in records
    } == {
        "customer_feedback",
        "user_reviews",
        "support_tickets",
    }


def test_normalizes_records_for_all_agents(tmp_path):
    create_three_datasets(tmp_path)

    records = load_feedback_dataset(tmp_path)

    record = records[0]

    assert record["feedback_id"] == "FB-001"
    assert record["id"] == "FB-001"
    assert record["source_channel"] == "Customer Feedback"
    assert record["raw_text"] == record["message"]
    assert record["title"]
    assert record["timestamp"].endswith("+00:00")


def test_duplicate_identical_records_are_removed(tmp_path):
    write_dataset(
        tmp_path,
        DATASET_FILES["customer_feedback"],
        [create_record("FB-001")],
    )

    write_dataset(
        tmp_path,
        DATASET_FILES["user_reviews"],
        [create_record("FB-001")],
    )

    write_dataset(
        tmp_path,
        DATASET_FILES["support_tickets"],
        [create_record("TKT-001")],
    )

    records = load_feedback_dataset(tmp_path)

    assert len(records) == 2

    ids = [record["feedback_id"] for record in records]

    assert len(ids) == len(set(ids))


def test_conflicting_duplicate_ids_are_rejected(tmp_path):
    write_dataset(
        tmp_path,
        DATASET_FILES["customer_feedback"],
        [create_record("FB-001", "The app is slow.")],
    )

    write_dataset(
        tmp_path,
        DATASET_FILES["user_reviews"],
        [create_record("FB-001", "The app is crashing.")],
    )

    write_dataset(
        tmp_path,
        DATASET_FILES["support_tickets"],
        [create_record("TKT-001")],
    )

    with pytest.raises(
        DatasetLoadError,
        match="Conflicting records",
    ):
        load_feedback_dataset(tmp_path)


def test_missing_dataset_file_is_rejected(tmp_path):
    write_dataset(
        tmp_path,
        DATASET_FILES["customer_feedback"],
        [create_record()],
    )

    with pytest.raises(DatasetLoadError, match="not found"):
        load_feedback_dataset(tmp_path)


def test_invalid_timestamp_is_rejected(tmp_path):
    invalid_record = create_record()
    invalid_record["timestamp"] = "not-a-date"

    write_dataset(
        tmp_path,
        DATASET_FILES["customer_feedback"],
        [invalid_record],
    )

    write_dataset(
        tmp_path,
        DATASET_FILES["user_reviews"],
        [],
    )

    write_dataset(
        tmp_path,
        DATASET_FILES["support_tickets"],
        [],
    )

    with pytest.raises(DatasetLoadError, match="timestamp"):
        load_feedback_dataset(tmp_path)


def test_loads_actual_project_datasets():
    records = load_feedback_dataset()

    assert records

    assert {
        record["dataset"] for record in records
    } == set(DATASET_FILES.keys())

    assert len(records) == len({
        record["feedback_id"] for record in records
    })


def test_default_dataset_path_exists():
    assert DEFAULT_DATASETS_DIR.is_dir()
