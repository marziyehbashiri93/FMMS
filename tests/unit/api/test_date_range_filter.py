"""Unit tests for the shared from_date/to_date query filter contract."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from interfaces.api.v1.filters import DateRangeFilterSerializer, date_range_to_datetimes


class TestDateRangeFilterSerializer:
    """Ensure date-filter endpoints accept both bounds consistently."""

    def test_accepts_both_from_and_to(self) -> None:
        serializer = DateRangeFilterSerializer(
            data={"from_date": "2026-07-01", "to_date": "2026-07-16"}
        )

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["from_date"] == date(2026, 7, 1)
        assert serializer.validated_data["to_date"] == date(2026, 7, 16)

    def test_accepts_from_only(self) -> None:
        serializer = DateRangeFilterSerializer(data={"from_date": "2026-07-16"})

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["from_date"] == date(2026, 7, 16)
        assert "to_date" not in serializer.validated_data

    def test_accepts_to_only(self) -> None:
        serializer = DateRangeFilterSerializer(data={"to_date": "2026-07-16"})

        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["to_date"] == date(2026, 7, 16)
        assert "from_date" not in serializer.validated_data

    def test_rejects_inverted_range(self) -> None:
        serializer = DateRangeFilterSerializer(
            data={"from_date": "2026-07-20", "to_date": "2026-07-16"}
        )

        assert not serializer.is_valid()
        assert "to_date" in serializer.errors

    def test_converts_to_inclusive_utc_datetimes(self) -> None:
        serializer = DateRangeFilterSerializer(
            data={"from_date": "2026-07-01", "to_date": "2026-07-16"}
        )
        assert serializer.is_valid(), serializer.errors

        start, end = date_range_to_datetimes(serializer)

        assert start == datetime(2026, 7, 1, 0, 0, 0, tzinfo=UTC)
        assert end == datetime.combine(date(2026, 7, 16), time.max, tzinfo=UTC)
