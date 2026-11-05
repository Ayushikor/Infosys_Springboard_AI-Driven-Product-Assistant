
"""
Automatic loader for the three project feedback datasets.

Reads only:
- datasets/customer_feedback.json
- datasets/user_reviews.json
- datasets/support_tickets.json

Does not read from MongoDB or write to any database.
"""

import json
import logging

from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Project root:
# Infosys_Springboard_AI-Driven-Product-Assistant/
PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_DATASETS_DIR = PROJECT_ROOT / "datasets"

DATASET_FILES = {
    "customer_feedback": "customer_feedback.json",
    "user_reviews": "user_reviews.json",
    "support_tickets": "support_tickets.json",
}


class DatasetLoadError(RuntimeError):
    """Raised when the feedback datasets cannot be loaded."""


def _required_text(
    record: dict[str, Any],
    field: str,
    dataset_name: str,
    record_number: int,
) -> str:
    """Read and validate a required text field."""

    value = record.get(field)

    if not isinstance(value, str) or not value.strip():
        raise DatasetLoadError(
            f"Invalid '{field}' in {dataset_name}, "
            f"record {record_number}."
        )

    return value.strip()


def _normalize_timestamp(
    value: str,
    dataset_name: str,
    record_number: int,
) -> str:
    """Validate and normalize an ISO timestamp."""

    try:
        timestamp = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("Timezone information is missing.")

        return timestamp.isoformat()

    except (ValueError, TypeError):
        raise DatasetLoadError(
            f"Invalid or timezone-naive timestamp in "
            f"{dataset_name}, record {record_number}: {value}"
        ) from None


def _derive_title(raw_text: str, limit: int = 80) -> str:
    """Generate a short title from the original feedback."""

    first_sentence = raw_text.split(".", 1)[0].strip()

    if len(first_sentence) <= limit:
        return first_sentence

    return first_sentence[:limit].rsplit(" ", 1)[0] + "..."


def _read_dataset(
    file_path: Path,
    dataset_name: str,
) -> list[dict[str, Any]]:
    """Read and normalize one JSON dataset."""

    if not file_path.exists():
        raise DatasetLoadError(
            f"Dataset file not found: {file_path}"
        )

    try:
        with file_path.open("r", encoding="utf-8") as file:
            records = json.load(file)

    except json.JSONDecodeError as exc:
        raise DatasetLoadError(
            f"Invalid JSON in {file_path.name}: {exc}"
        ) from exc

    except OSError as exc:
        raise DatasetLoadError(
            f"Could not read {file_path.name}: {exc}"
        ) from exc

    if not isinstance(records, list):
        raise DatasetLoadError(
            f"{file_path.name} must contain a JSON array."
        )

    normalized_records = []

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise DatasetLoadError(
                f"Invalid record {index} in {file_path.name}."
            )

        feedback_id = _required_text(
            record,
            "feedback_id",
            dataset_name,
            index,
        )

        source_channel = _required_text(
            record,
            "source_channel",
            dataset_name,
            index,
        )

        raw_text = _required_text(
            record,
            "raw_text",
            dataset_name,
            index,
        )

        raw_timestamp = _required_text(
            record,
            "timestamp",
            dataset_name,
            index,
        )

        timestamp = _normalize_timestamp(
            raw_timestamp,
            dataset_name,
            index,
        )

        # Unified format used by the four agents.
        normalized_records.append({
            "feedback_id": feedback_id,
            "id": feedback_id,
            "source_channel": source_channel,
            "raw_text": raw_text,
            "title": _derive_title(raw_text),
            "message": raw_text,
            "timestamp": timestamp,
            "dataset": dataset_name,
        })

    logger.info(
        "Loaded %d records from %s.",
        len(normalized_records),
        file_path.name,
    )

    return normalized_records


def load_feedback_dataset(
    datasets_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """
    Load, normalize and deduplicate all three project datasets.

    Returns:
        A unified list of feedback records.

    Raises:
        DatasetLoadError: If a file is missing, malformed,
        contains invalid records, or contains conflicting IDs.
    """

    directory = (
        Path(datasets_dir)
        if datasets_dir is not None
        else DEFAULT_DATASETS_DIR
    )

    if not directory.is_dir():
        raise DatasetLoadError(
            f"Datasets directory not found: {directory}"
        )

    all_records = []
    records_by_id = {}

    total_before_deduplication = 0

    for dataset_name, filename in DATASET_FILES.items():
        file_path = directory / filename

        records = _read_dataset(
            file_path,
            dataset_name,
        )

        total_before_deduplication += len(records)

        for record in records:
            feedback_id = record["feedback_id"]

            existing = records_by_id.get(feedback_id)

            if existing is not None:

                # Identical records are included only once.
                comparable_fields = (
                    "source_channel",
                    "raw_text",
                    "timestamp",
                )

                identical = all(
                    existing[field] == record[field]
                    for field in comparable_fields
                )

                if identical:
                    logger.warning(
                        "Skipping duplicate feedback ID: %s",
                        feedback_id,
                    )
                    continue

                # Do not silently discard conflicting records.
                raise DatasetLoadError(
                    f"Conflicting records found for feedback ID "
                    f"'{feedback_id}'."
                )

            records_by_id[feedback_id] = record
            all_records.append(record)

    if not all_records:
        raise DatasetLoadError(
            "No feedback records were found in the datasets."
        )

    logger.info(
        "Dataset loading completed. "
        "Records before deduplication: %d. "
        "Unique records: %d.",
        total_before_deduplication,
        len(all_records),
    )

    return all_records
