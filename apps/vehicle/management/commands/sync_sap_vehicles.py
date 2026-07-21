"""Synchronize FMMS vehicles and assigned drivers from SAP."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandParser

from interfaces.api.v1 import deps


class Command(BaseCommand):
    """Run the existing vehicle SAP sync service from the command line."""

    help = "Synchronize FMMS vehicles and assigned drivers from SAP."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--plant",
            default=None,
            help="Optional SAP plant filter.",
        )

    def handle(self, *args: object, **options: object) -> None:
        plant = options.get("plant")
        result = deps.get_sync_vehicles_from_sap_service().execute(
            request_id="manage-sync-sap-vehicles",
            plant=str(plant) if plant else None,
        )
        self.stdout.write(
            self.style.SUCCESS(
                "SAP vehicle sync completed: "
                f"total={result.total_received}, "
                f"created={result.created}, "
                f"updated={result.updated}, "
                f"decommissioned={result.decommissioned}, "
                f"failed={result.failed}"
            )
        )
