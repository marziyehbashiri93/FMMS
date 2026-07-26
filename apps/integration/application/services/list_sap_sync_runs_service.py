"""Query-side service for listing SAP read-sync run history."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apps.integration.infrastructure.models import SAPSyncRunModel


@dataclass(frozen=True)
class SAPSyncRunItemHistoryDTO:
    """Output DTO for one persisted SAP sync item result."""

    id: str
    name: str
    status: str
    started_at: datetime
    finished_at: datetime
    summary: dict[str, Any]
    error: str | None


@dataclass(frozen=True)
class SAPSyncRunHistoryDTO:
    """Output DTO for one persisted SAP sync run."""

    id: str
    trigger_source: str
    status: str
    request_id: str
    triggered_by: str | None
    started_at: datetime
    finished_at: datetime | None
    summary: dict[str, Any]
    error: str | None
    items: list[SAPSyncRunItemHistoryDTO]


class ListSAPSyncRunsService:
    """List persisted SAP read-sync runs in newest-first order."""

    def execute(self) -> list[SAPSyncRunHistoryDTO]:
        """Return non-deleted SAP sync runs with item results."""
        runs = (
            SAPSyncRunModel.objects.filter(is_deleted=False)
            .prefetch_related("items")
            .order_by("-started_at")
        )
        return [_to_history_dto(run) for run in runs]


def _to_history_dto(run: SAPSyncRunModel) -> SAPSyncRunHistoryDTO:
    """Map a persisted sync run to a response DTO."""
    items = [
        SAPSyncRunItemHistoryDTO(
            id=str(item.id),
            name=item.name,
            status=item.status,
            started_at=item.started_at,
            finished_at=item.finished_at,
            summary=item.summary,
            error=item.error_message or None,
        )
        for item in sorted(run.items.all(), key=lambda item: item.started_at)
        if not item.is_deleted
    ]
    return SAPSyncRunHistoryDTO(
        id=str(run.id),
        trigger_source=run.trigger_source,
        status=run.status,
        request_id=run.request_id,
        triggered_by=str(run.triggered_by_id) if run.triggered_by_id else None,
        started_at=run.started_at,
        finished_at=run.finished_at,
        summary=run.summary,
        error=run.error_message or None,
        items=items,
    )
