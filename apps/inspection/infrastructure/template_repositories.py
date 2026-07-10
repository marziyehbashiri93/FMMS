"""Concrete Django ORM implementation of IInspectionTemplateRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.inspection.domain.interfaces.inspection_template_repository import (
    IInspectionTemplateRepository,
)
from apps.inspection.domain.template_entities import InspectionTemplate
from apps.inspection.infrastructure.models import InspectionTemplateModel
from core.domain.exceptions import DomainNotFoundError
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="inspection", module=__name__)


def _to_domain(orm: InspectionTemplateModel) -> InspectionTemplate:
    """Map ORM row to domain entity."""
    return InspectionTemplate(
        id=uuid.UUID(str(orm.id)),
        sap_code=orm.sap_code,
        code_group=orm.code_group,
        category=orm.category,
        description=orm.description,
        catalog_type=orm.catalog_type,
        is_active=orm.is_active,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class DjangoInspectionTemplateRepository(IInspectionTemplateRepository):
    """ORM-backed repository for inspection checklist templates."""

    def get_by_id(self, template_id: uuid.UUID) -> InspectionTemplate:
        """Retrieve a template by UUID."""
        try:
            orm = InspectionTemplateModel.objects.get(id=template_id, is_deleted=False)
        except InspectionTemplateModel.DoesNotExist as exc:
            raise DomainNotFoundError(
                f"Inspection template '{template_id}' not found."
            ) from exc
        return _to_domain(orm)

    def get_by_sap_key(
        self, sap_code: str, code_group: str, catalog_type: str
    ) -> InspectionTemplate | None:
        """Retrieve a template by SAP natural key."""
        orm = InspectionTemplateModel.objects.filter(
            sap_code=sap_code,
            code_group=code_group,
            catalog_type=catalog_type,
            is_deleted=False,
        ).first()
        return _to_domain(orm) if orm else None

    def list_active(self) -> list[InspectionTemplate]:
        """Return all active templates ordered by category then description."""
        qs = InspectionTemplateModel.objects.filter(
            is_active=True, is_deleted=False
        ).order_by("category", "description")
        return [_to_domain(orm) for orm in qs]

    def save(self, template: InspectionTemplate) -> InspectionTemplate:
        """Persist a new or updated template."""
        defaults = {
            "sap_code": template.sap_code,
            "code_group": template.code_group,
            "category": template.category,
            "description": template.description,
            "catalog_type": template.catalog_type,
            "is_active": template.is_active,
            "updated_at": datetime.now(tz=UTC),
        }
        obj, created = InspectionTemplateModel.objects.update_or_create(
            id=template.id,
            defaults=defaults,
        )
        if created:
            obj.created_at = template.created_at
            obj.save(update_fields=["created_at"])
        logger.debug(
            "saved inspection template",
            extra={"template_id": str(template.id), "is_new": created},
        )
        return template
