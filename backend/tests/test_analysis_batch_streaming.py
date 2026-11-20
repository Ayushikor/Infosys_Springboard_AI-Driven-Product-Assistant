
import pytest

from services.analysis_service import (
    AnalysisServiceError,
    _iter_document_batches,
    _validate_feedback_count,
)


class CountingCursor:
    """Simulate a lazy MongoDB cursor."""

    def __init__(self, total):
        self.total = total
        self.position = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.position >= self.total:
            raise StopIteration

        record = {
            "id": f"FB-{self.position:05d}",
            "position": self.position,
        }

        self.position += 1
        return record


def test_10000_records_use_50_batches():
    cursor = CountingCursor(10_000)

    batches = _iter_document_batches(
        cursor,
        total_records=10_000,
        batch_size=200,
    )

    first_index, first_batch = next(batches)

    assert first_index == 1
    assert len(first_batch) == 200

    # Only the first batch should have been consumed.
    assert cursor.position == 200

    sizes = [len(first_batch)]

    for _, batch in batches:
        sizes.append(len(batch))

    assert len(sizes) == 50
    assert all(size == 200 for size in sizes)
    assert cursor.position == 10_000


def test_401_records_are_balanced():
    cursor = CountingCursor(401)

    batches = list(
        _iter_document_batches(
            cursor,
            total_records=401,
            batch_size=200,
        )
    )

    assert [len(batch) for _, batch in batches] == [
        134, 134, 133
    ]


def test_exactly_10000_records_is_allowed():
    _validate_feedback_count(10_000)


def test_more_than_10000_records_is_rejected():
    with pytest.raises(AnalysisServiceError) as exc:
        _validate_feedback_count(10_001)

    assert exc.value.status_code == 422


def test_less_than_two_records_is_rejected():
    with pytest.raises(AnalysisServiceError) as exc:
        _validate_feedback_count(1)

    assert exc.value.status_code == 422
