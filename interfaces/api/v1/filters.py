"""Shared API query filters for FMMS v1 endpoints."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from rest_framework import serializers


class DateRangeFilterSerializer(serializers.Serializer):
    """Optional inclusive date-range query params used by all date-filter APIs.

    Endpoints that filter by date MUST accept both ``from_date`` and ``to_date``.
    Either bound may be omitted independently; when both are present,
    ``from_date`` must be less than or equal to ``to_date``.
    """

    from_date = serializers.DateField(
        required=False,
        help_text="Inclusive range start (YYYY-MM-DD).",
    )
    to_date = serializers.DateField(
        required=False,
        help_text="Inclusive range end (YYYY-MM-DD).",
    )

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Ensure the date range is chronologically valid."""
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError(
                {"to_date": "to_date must be greater than or equal to from_date."}
            )
        return attrs


def date_range_to_datetimes(
    filters: DateRangeFilterSerializer,
) -> tuple[datetime | None, datetime | None]:
    """Convert validated date bounds to inclusive UTC datetime bounds."""
    from_date = filters.validated_data.get("from_date")
    to_date = filters.validated_data.get("to_date")
    from_datetime = (
        datetime.combine(from_date, time.min, tzinfo=UTC)
        if isinstance(from_date, date)
        else None
    )
    to_datetime = (
        datetime.combine(to_date, time.max, tzinfo=UTC)
        if isinstance(to_date, date)
        else None
    )
    return from_datetime, to_datetime
