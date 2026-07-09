"""Unit tests for domain→application exception translation helpers."""

from __future__ import annotations

import pytest

from apps.vehicle.domain.exceptions import VehicleNotFoundError
from core.domain.exceptions import DomainStateError
from core.exceptions.base_exception import FMMSNotFoundError
from core.exceptions.translation import load_or_not_found


@pytest.mark.unit
class TestLoadOrNotFound:
    """``load_or_not_found`` maps domain not-found and None to FMMSNotFoundError."""

    def test_returns_entity_on_success(self) -> None:
        """Successful loaders pass through unchanged."""
        assert load_or_not_found(lambda: "ok", message="missing") == "ok"

    def test_none_raises_fmms_not_found(self) -> None:
        """Test doubles that return None are translated."""
        with pytest.raises(FMMSNotFoundError) as exc_info:
            load_or_not_found(
                lambda: None,
                message="Vehicle gone",
                details={"vehicle_id": "x"},
            )
        assert exc_info.value.error_code == "NOT_FOUND"
        assert exc_info.value.details == {"vehicle_id": "x"}

    def test_domain_not_found_raises_fmms_not_found(self) -> None:
        """Production repos raising DomainNotFoundError are translated."""
        with pytest.raises(FMMSNotFoundError) as exc_info:
            load_or_not_found(
                lambda: (_ for _ in ()).throw(VehicleNotFoundError("abc")),
                message="Vehicle 'abc' not found.",
                details={"vehicle_id": "abc"},
            )
        assert "abc" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, VehicleNotFoundError)


@pytest.mark.unit
class TestDomainStateHierarchy:
    """State exceptions share DomainStateError for HTTP category mapping."""

    def test_repair_invalid_transition_is_domain_state_error(self) -> None:
        """Repair state transitions are DomainStateError subclasses."""
        from apps.repair.domain.exceptions import RepairOrderInvalidStateTransitionError

        err = RepairOrderInvalidStateTransitionError("CREATED", "IN_PROGRESS")
        assert isinstance(err, DomainStateError)
