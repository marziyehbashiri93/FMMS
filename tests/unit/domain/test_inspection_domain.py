"""Unit tests for the Inspection domain layer."""

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
from apps.inspection.domain.exceptions import (
    InspectionAlreadySubmittedError,
    InspectionInvalidStateTransitionError,
    InspectionItemRequiredError,
)
from apps.inspection.domain.value_objects import (
    ChecklistResult,
    InspectionScore,
    OdometerReading,
    OdometerUnit,
)


def _make_inspection(**kwargs: object) -> Inspection:
    defaults: dict[str, object] = {
        "id": uuid.uuid4(),
        "vehicle_id": uuid.uuid4(),
        "inspection_type": InspectionType.PRE_TRIP,
        "odometer_reading": OdometerReading(value=50000, unit=OdometerUnit.KM),
        "status": InspectionStatus.DRAFT,
        "inspected_at": datetime.now(tz=UTC),
        "created_at": datetime.now(tz=UTC),
        "updated_at": datetime.now(tz=UTC),
    }
    defaults.update(kwargs)
    return Inspection(**defaults)  # type: ignore[arg-type]


def _make_item(result: ChecklistResult = ChecklistResult.PASS) -> InspectionItem:
    return InspectionItem(
        id=uuid.uuid4(),
        category="Brakes",
        description="Check brake pad thickness.",
        result=result,
    )


class TestOdometerReading:
    def test_valid(self) -> None:
        r = OdometerReading(value=10000, unit=OdometerUnit.KM)
        assert r.value == 10000
        assert str(r) == "10000 KM"

    def test_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="non-negative"):
            OdometerReading(value=-1, unit=OdometerUnit.KM)

    def test_zero_valid(self) -> None:
        r = OdometerReading(value=0, unit=OdometerUnit.KM)
        assert r.value == 0


class TestInspectionScore:
    def test_full_pass(self) -> None:
        score = InspectionScore.compute(passed=10, total=10)
        assert score.value == 100.0

    def test_half_pass(self) -> None:
        score = InspectionScore.compute(passed=5, total=10)
        assert score.value == 50.0

    def test_zero_total_raises(self) -> None:
        with pytest.raises(ValueError, match="greater than 0"):
            InspectionScore.compute(passed=0, total=0)

    def test_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="between 0 and 100"):
            InspectionScore(value=101.0)


class TestInspectionLifecycle:
    def test_initial_draft(self) -> None:
        insp = _make_inspection()
        assert insp.status == InspectionStatus.DRAFT

    def test_add_item(self) -> None:
        insp = _make_inspection()
        insp.add_item(_make_item())
        assert len(insp.items) == 1

    def test_submit_no_items_raises(self) -> None:
        insp = _make_inspection()
        with pytest.raises(InspectionItemRequiredError):
            insp.submit()

    def test_submit_with_items(self) -> None:
        insp = _make_inspection()
        insp.add_item(_make_item())
        insp.submit()
        assert insp.status == InspectionStatus.SUBMITTED

    def test_add_item_after_submit_raises(self) -> None:
        insp = _make_inspection()
        insp.add_item(_make_item())
        insp.submit()
        with pytest.raises(InspectionAlreadySubmittedError):
            insp.add_item(_make_item())

    def test_approve(self) -> None:
        insp = _make_inspection(status=InspectionStatus.SUBMITTED)
        reviewer = uuid.uuid4()
        insp.approve(reviewed_by_id=reviewer, notes="Looks good.")
        assert insp.status == InspectionStatus.APPROVED
        assert insp.reviewed_by_id == reviewer

    def test_reject(self) -> None:
        insp = _make_inspection(status=InspectionStatus.SUBMITTED)
        reviewer = uuid.uuid4()
        insp.reject(reviewed_by_id=reviewer, notes="Issues found.")
        assert insp.status == InspectionStatus.REJECTED

    def test_reopen_rejected(self) -> None:
        insp = _make_inspection(status=InspectionStatus.REJECTED)
        insp.reviewed_by_id = uuid.uuid4()
        insp.reopen()
        assert insp.status == InspectionStatus.DRAFT
        assert insp.reviewed_by_id is None

    def test_invalid_transition_draft_to_approved(self) -> None:
        insp = _make_inspection()
        with pytest.raises(InspectionInvalidStateTransitionError):
            insp.approve(reviewed_by_id=uuid.uuid4())

    def test_score_all_pass(self) -> None:
        insp = _make_inspection()
        insp.add_item(_make_item(ChecklistResult.PASS))
        insp.add_item(_make_item(ChecklistResult.PASS))
        score = insp.score
        assert score is not None
        assert score.value == 100.0

    def test_has_failures(self) -> None:
        insp = _make_inspection()
        insp.add_item(_make_item(ChecklistResult.FAIL))
        assert insp.has_failures is True

    def test_score_excludes_na_items(self) -> None:
        insp = _make_inspection()
        insp.add_item(_make_item(ChecklistResult.PASS))
        insp.add_item(_make_item(ChecklistResult.NOT_APPLICABLE))
        score = insp.score
        assert score is not None
        assert score.value == 100.0

    def test_score_none_when_all_na(self) -> None:
        insp = _make_inspection()
        insp.add_item(_make_item(ChecklistResult.NOT_APPLICABLE))
        assert insp.score is None
