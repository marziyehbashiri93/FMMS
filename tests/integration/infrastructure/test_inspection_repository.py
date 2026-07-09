"""Integration tests for DjangoInspectionRepository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from apps.inspection.domain.entities import (
    Inspection,
    InspectionItem,
    InspectionStatus,
    InspectionType,
)
from apps.inspection.domain.exceptions import InspectionNotFoundError
from apps.inspection.domain.interfaces.inspection_repository import (
    IInspectionRepository,
)
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    OdometerReading,
    OdometerUnit,
)
from apps.inspection.infrastructure.repositories import DjangoInspectionRepository

pytestmark = pytest.mark.django_db


def _make_inspection(
    vehicle_id: uuid.UUID | None = None,
    status: InspectionStatus = InspectionStatus.DRAFT,
    items: list[InspectionItem] | None = None,
) -> Inspection:
    repo = DjangoInspectionRepository()
    inspection = Inspection(
        id=uuid.uuid4(),
        vehicle_id=vehicle_id or uuid.uuid4(),
        inspection_type=InspectionType.PERIODIC,
        odometer_reading=OdometerReading(value=50000, unit=OdometerUnit.KM),
        status=status,
        inspected_at=datetime.now(tz=UTC),
        created_at=datetime.now(tz=UTC),
        updated_at=datetime.now(tz=UTC),
        items=items or [],
    )
    return repo.save(inspection)


def _item(result: ChecklistResult = ChecklistResult.PASS) -> InspectionItem:
    return InspectionItem(
        id=uuid.uuid4(),
        category="Brakes",
        description="Brake pads OK",
        result=result,
    )


class TestInterface:
    def test_satisfies_interface(self) -> None:
        assert isinstance(DjangoInspectionRepository(), IInspectionRepository)


class TestSaveAndRetrieve:
    def test_save_and_get_by_id(self) -> None:
        repo = DjangoInspectionRepository()
        insp = _make_inspection()
        fetched = repo.get_by_id(insp.id)
        assert fetched.id == insp.id
        assert fetched.status == InspectionStatus.DRAFT
        assert fetched.odometer_reading.value == 50000

    def test_get_by_id_not_found(self) -> None:
        repo = DjangoInspectionRepository()
        with pytest.raises(InspectionNotFoundError):
            repo.get_by_id(uuid.uuid4())

    def test_items_persisted_and_retrieved(self) -> None:
        repo = DjangoInspectionRepository()
        items = [_item(ChecklistResult.PASS), _item(ChecklistResult.FAIL)]
        insp = _make_inspection(items=items)
        fetched = repo.get_by_id(insp.id)
        assert len(fetched.items) == 2

    def test_items_replaced_on_resave(self) -> None:
        """Replacing items on update does not leave orphans."""
        repo = DjangoInspectionRepository()
        insp = _make_inspection(items=[_item()])
        insp.items = [_item(ChecklistResult.FAIL), _item(ChecklistResult.PASS)]
        repo.save(insp)
        fetched = repo.get_by_id(insp.id)
        assert len(fetched.items) == 2

    def test_status_update_persisted(self) -> None:
        repo = DjangoInspectionRepository()
        items = [_item()]
        insp = _make_inspection(items=items)
        insp.submit()
        repo.save(insp)
        fetched = repo.get_by_id(insp.id)
        assert fetched.status == InspectionStatus.SUBMITTED


class TestListByVehicle:
    def test_list_by_vehicle(self) -> None:
        repo = DjangoInspectionRepository()
        vid = uuid.uuid4()
        _make_inspection(vehicle_id=vid)
        _make_inspection(vehicle_id=vid)
        _make_inspection()
        result = repo.list_by_vehicle(vid)
        assert len(result) == 2
        assert all(i.vehicle_id == vid for i in result)

    def test_list_by_vehicle_filter_status(self) -> None:
        repo = DjangoInspectionRepository()
        vid = uuid.uuid4()
        items = [_item()]
        insp_draft = _make_inspection(vehicle_id=vid, items=items)
        insp_draft.submit()
        repo.save(insp_draft)
        _make_inspection(vehicle_id=vid)
        submitted = repo.list_by_vehicle(vid, status=InspectionStatus.SUBMITTED)
        assert all(i.status == InspectionStatus.SUBMITTED for i in submitted)
        assert len(submitted) == 1


class TestSoftDelete:
    def test_delete_hides_inspection(self) -> None:
        repo = DjangoInspectionRepository()
        insp = _make_inspection()
        repo.delete(insp.id)
        with pytest.raises(InspectionNotFoundError):
            repo.get_by_id(insp.id)

    def test_delete_nonexistent_raises(self) -> None:
        repo = DjangoInspectionRepository()
        with pytest.raises(InspectionNotFoundError):
            repo.delete(uuid.uuid4())
