"""Infrastructure repositories for material requests."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from apps.material.domain.entities import (
    MaterialRequest,
    MaterialRequestItem,
    MaterialRequestStatus,
)
from apps.material.domain.exceptions import MaterialRequestNotFoundError
from apps.material.domain.interfaces.inventory_transaction_repository import (
    IInventoryTransactionRepository,
)
from apps.material.domain.interfaces.material_request_repository import (
    IMaterialRequestRepository,
)
from apps.material.infrastructure.models import (
    InventoryTransactionModel,
    MaterialRequestItemModel,
    MaterialRequestModel,
)


def _to_domain(orm: MaterialRequestModel) -> MaterialRequest:
    """Map ORM model to aggregate."""
    return MaterialRequest(
        id=orm.id,
        repair_order_id=orm.repair_order_id,
        status=MaterialRequestStatus(orm.status),
        created_by_id=orm.requested_by_id,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
        items=[
            MaterialRequestItem(
                id=item.item_id,
                material_number=item.material_number,
                quantity=item.quantity,
                unit_of_measure=item.unit_of_measure,
            )
            for item in orm.items.all()
        ],
    )


class DjangoMaterialRequestRepository(IMaterialRequestRepository):
    """Django-backed material request repository."""

    def get_by_id(self, request_id: uuid.UUID) -> MaterialRequest:
        """Get one material request."""
        try:
            orm = MaterialRequestModel.objects.get(id=request_id, is_deleted=False)
        except MaterialRequestModel.DoesNotExist:
            raise MaterialRequestNotFoundError(request_id) from None
        return _to_domain(orm)

    def list_all(
        self, *, status: MaterialRequestStatus | None = None
    ) -> list[MaterialRequest]:
        """List material requests by optional status."""
        qs = MaterialRequestModel.objects.filter(is_deleted=False)
        if status is not None:
            qs = qs.filter(status=status.value)
        return [_to_domain(item) for item in qs]

    def list_by_repair_order(self, repair_order_id: uuid.UUID) -> list[MaterialRequest]:
        """List material requests by repair order."""
        qs = MaterialRequestModel.objects.filter(
            repair_order_id=repair_order_id, is_deleted=False
        )
        return [_to_domain(item) for item in qs]

    def save(self, material_request: MaterialRequest) -> MaterialRequest:
        """Persist material request aggregate."""
        orm, created = MaterialRequestModel.objects.update_or_create(
            id=material_request.id,
            defaults={
                "repair_order_id": material_request.repair_order_id,
                "status": material_request.status.value,
                "requested_by_id": material_request.created_by_id,
                "updated_at": datetime.now(tz=UTC),
            },
        )
        if created:
            orm.created_at = material_request.created_at
            orm.save(update_fields=["created_at"])

        orm.items.all().delete()
        MaterialRequestItemModel.objects.bulk_create(
            [
                MaterialRequestItemModel(
                    material_request=orm,
                    item_id=item.id,
                    material_number=item.material_number,
                    quantity=item.quantity,
                    unit_of_measure=item.unit_of_measure,
                )
                for item in material_request.items
            ]
        )
        return material_request


class DjangoInventoryTransactionRepository(IInventoryTransactionRepository):
    """Persist inventory issue placeholders."""

    def create_issue_for_material_request(self, material_request_id: uuid.UUID) -> None:
        """Create placeholder stock issue transaction."""
        InventoryTransactionModel.objects.create(
            material_request_id=material_request_id,
            quantity=Decimal("0"),
            transaction_type="STOCK_ISSUE",
        )
