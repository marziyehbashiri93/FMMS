"""Unit tests for SAP environment configuration."""

from __future__ import annotations

from infrastructure.sap.config import SAPConfig


def test_vehicle_driver_new_env_vars_take_priority(monkeypatch) -> None:
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ODATA_SERVICE", "NEW_SERVICE")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ODATA_ENTITY", "NewEntity")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_SERVICE", "OLD_SERVICE")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ENTITY_SET", "OldEntity")

    config = SAPConfig.from_env()

    assert config.vehicle_driver_service == "NEW_SERVICE"
    assert config.vehicle_driver_entity_set == "NewEntity"


def test_vehicle_driver_old_env_vars_are_fallback(monkeypatch) -> None:
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_ENTITY", raising=False)
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_SERVICE", "OLD_SERVICE")
    monkeypatch.setenv("SAP_VEHICLE_DRIVER_ENTITY_SET", "OldEntity")

    config = SAPConfig.from_env()

    assert config.vehicle_driver_service == "OLD_SERVICE"
    assert config.vehicle_driver_entity_set == "OldEntity"


def test_vehicle_driver_defaults_match_current_cds_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ODATA_ENTITY", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_SERVICE", raising=False)
    monkeypatch.delenv("SAP_VEHICLE_DRIVER_ENTITY_SET", raising=False)

    config = SAPConfig.from_env()

    assert config.vehicle_driver_service == "ZC_VEHICLEDRIVER_CDS"
    assert config.vehicle_driver_entity_set == "ZC_VehicleDriver"


def test_sap_write_defaults_to_enabled(monkeypatch) -> None:
    monkeypatch.delenv("SAP_WRITE", raising=False)
    monkeypatch.delenv("SAP_write", raising=False)

    config = SAPConfig.from_env()

    assert config.write_enabled is True


def test_sap_write_can_be_disabled(monkeypatch) -> None:
    monkeypatch.setenv("SAP_WRITE", "False")

    config = SAPConfig.from_env()

    assert config.write_enabled is False


def test_sap_write_lowercase_alias_is_supported(monkeypatch) -> None:
    monkeypatch.delenv("SAP_WRITE", raising=False)
    monkeypatch.setenv("SAP_write", "False")

    config = SAPConfig.from_env()

    assert config.write_enabled is False
