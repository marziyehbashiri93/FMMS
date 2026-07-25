"""Map material-request aggregates to enriched response DTOs."""

from __future__ import annotations

from decimal import Decimal

from apps.material.application.dto.material_request_dto import (
    MaterialRequestItemResponseDTO,
    MaterialRequestResponseDTO,
)
from apps.material.domain.entities import MaterialRequest
from apps.material.domain.interfaces.central_stock_repository import (
    ICentralStockRepository,
)


def to_material_request_response(
    material_request: MaterialRequest,
    stock_repository: ICentralStockRepository | None = None,
) -> MaterialRequestResponseDTO:
    """Map aggregate to response DTO, optionally enriching with live KH08 stock."""
    return MaterialRequestResponseDTO(
        id=material_request.id,
        repair_order_id=material_request.repair_order_id,
        status=material_request.status,
        created_by_id=material_request.created_by_id,
        created_at=material_request.created_at,
        updated_at=material_request.updated_at,
        items=[
            _to_item_response(item, stock_repository)
            for item in material_request.items
        ],
    )


def _to_item_response(
    item,
    stock_repository: ICentralStockRepository | None,
) -> MaterialRequestItemResponseDTO:
    """Map one item with optional live stock fields."""
    available = Decimal("0")
    in_catalog = bool(item.from_catalog)
    material_name = ""
    if stock_repository is not None:
        available = stock_repository.get_available_quantity(item.material_number)
        in_catalog = stock_repository.material_exists(item.material_number)
        material_name = stock_repository.get_material_name(item.material_number)
    return MaterialRequestItemResponseDTO(
        id=item.id,
        material_number=item.material_number,
        quantity=item.quantity,
        unit_of_measure=item.unit_of_measure,
        from_catalog=bool(item.from_catalog),
        decision=item.decision,
        item_status=item.item_status,
        material_name=material_name,
        available_quantity=available,
        in_catalog=in_catalog,
        available_quantity_snapshot=item.available_quantity_snapshot,
    )
