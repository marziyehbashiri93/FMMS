"""Unit tests for inspection checklist template sync/list services."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.inspection.application.services.sync_inspection_templates_from_sap_service import (
    ListInspectionTemplatesService,
    SyncInspectionTemplatesFromSAPService,
)
from apps.inspection.domain.interfaces.inspection_template_repository import (
    IInspectionTemplateRepository,
)
from apps.inspection.domain.template_entities import InspectionTemplate
from core.sap.dtos.object_part_catalog import SAPObjectPartDTO
from core.sap.ports.object_part_catalog_port import ISAPObjectPartCatalogPort


class FakeTemplateRepository(IInspectionTemplateRepository):
    """In-memory inspection template repository."""

    def __init__(self, initial: list[InspectionTemplate] | None = None) -> None:
        self._store: dict[uuid.UUID, InspectionTemplate] = {
            t.id: t for t in (initial or [])
        }

    def get_by_id(self, template_id: uuid.UUID) -> InspectionTemplate | None:
        return self._store.get(template_id)

    def get_by_sap_key(
        self, code: str, code_group: str, catalog_type: str
    ) -> InspectionTemplate | None:
        return next(
            (
                t
                for t in self._store.values()
                if t.code == code
                and t.code_group == code_group
                and t.catalog_type == catalog_type
            ),
            None,
        )

    def list_active(self) -> list[InspectionTemplate]:
        return [t for t in self._store.values() if t.is_active]

    def save(self, template: InspectionTemplate) -> InspectionTemplate:
        self._store[template.id] = template
        return template


class FakeObjectPartCatalogPort(ISAPObjectPartCatalogPort):
    """Returns canned SAP object-part catalog entries."""

    def __init__(self, entries: list[SAPObjectPartDTO] | None = None) -> None:
        self._entries = entries or []

    def get_catalog(self, catalog_type: str) -> list[SAPObjectPartDTO]:
        return [e for e in self._entries if e.catalog_type == catalog_type]

    def get_part_by_code(
        self, code: str, code_group: str, catalog_type: str
    ) -> SAPObjectPartDTO:
        return next(
            e
            for e in self._entries
            if e.code == code
            and e.code_group == code_group
            and e.catalog_type == catalog_type
        )


def _entry(code: str, group: str, text: str) -> SAPObjectPartDTO:
    return SAPObjectPartDTO(
        code_group=group,
        code=code,
        group_text=group,
        code_text=text,
        defect_class="S2",
        defect_class_text="Major / جدی",
        catalog_type="B",
    )


class TestSyncInspectionTemplatesFromSAPService:
    def test_creates_templates_from_sap_catalog(self) -> None:
        repo = FakeTemplateRepository()
        sap = FakeObjectPartCatalogPort(
            [
                _entry("SEAT", "SAFETY", "Seat belt"),
                _entry("FLIGHT", "LIGHTS", "Front light"),
                _entry("FRIDGE", "CARGO", "Refrigerator"),
                _entry("SAFE", "SAFETY", "Safety equipment"),
            ]
        )

        result = SyncInspectionTemplatesFromSAPService(repo, sap).execute()

        assert result.total_received == 4
        assert result.created == 4
        assert result.updated == 0
        assert result.failed == 0
        assert len(repo.list_active()) == 4

    def test_updates_existing_template(self) -> None:
        now = datetime.now(tz=UTC)
        existing = InspectionTemplate(
            id=uuid.uuid4(),
            code_group="SAFETY",
            code="SEAT",
            group_text="SAFETY",
            code_text="Old seat belt text",
            defect_class="S3",
            defect_class_text="Minor / جزئی",
            catalog_type="B",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        repo = FakeTemplateRepository(initial=[existing])
        sap = FakeObjectPartCatalogPort([_entry("SEAT", "SAFETY", "Seat belt")])

        result = SyncInspectionTemplatesFromSAPService(repo, sap).execute()

        assert result.created == 0
        assert result.updated == 1
        assert repo.get_by_id(existing.id).code_text == "Seat belt"
        assert repo.get_by_id(existing.id).defect_class == "S2"

    def test_sync_is_idempotent(self) -> None:
        repo = FakeTemplateRepository()
        sap = FakeObjectPartCatalogPort([_entry("SEAT", "SAFETY", "Seat belt")])
        service = SyncInspectionTemplatesFromSAPService(repo, sap)

        first = service.execute()
        second = service.execute()

        assert first.created == 1
        assert second.created == 0
        assert second.updated == 1
        assert len(repo.list_active()) == 1


class TestListInspectionTemplatesService:
    def test_lists_active_templates(self) -> None:
        now = datetime.now(tz=UTC)
        active = InspectionTemplate(
            id=uuid.uuid4(),
            code_group="SAFETY",
            code="SEAT",
            group_text="SAFETY",
            code_text="Seat belt",
            defect_class="S2",
            defect_class_text="Major / جدی",
            catalog_type="B",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        inactive = InspectionTemplate(
            id=uuid.uuid4(),
            code_group="SAFETY",
            code="OLD",
            group_text="SAFETY",
            code_text="Retired item",
            defect_class="S3",
            defect_class_text="Minor / جزئی",
            catalog_type="B",
            is_active=False,
            created_at=now,
            updated_at=now,
        )
        repo = FakeTemplateRepository(initial=[active, inactive])

        result = ListInspectionTemplatesService(repo).execute()

        assert len(result) == 1
        assert result[0].code_text == "Seat belt"
