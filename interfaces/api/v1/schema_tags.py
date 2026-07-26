"""Shared OpenAPI tag names for API v1."""

from __future__ import annotations


class APITags:
    """Stable Swagger tag names grouped by FMMS app."""

    auth = "auth"
    vehicle = "vehicle"
    driver = "driver"
    inspection = "inspection"
    fault = "fault"
    repair = "repair"
    material = "material"
    handover = "handover"
    preventive_maintenance = "preventive-maintenance"
    procurement = "procurement"
    integration = "integration"


API_TAGS = APITags()
