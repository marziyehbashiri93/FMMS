"""Core SAP package.

This package contains the technology-independent SAP abstraction layer:

- ``core.sap.ports``: Abstract port interfaces (ABCs) that application services
  import to interact with SAP. No transport details here.
- ``core.sap.dtos``: Pure Python data transfer objects that cross the SAP boundary.
  No ORM models, no domain entities.

Infrastructure adapters that implement the ports live in
``infrastructure.sap.adapters`` and are never imported by application services.
"""
