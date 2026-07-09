# FMMS Documentation Index

> All project documentation is maintained in this directory.
> This index is the starting point for navigating FMMS documentation.

---

## Architecture & Design

| Document | Description | Audience |
|---|---|---|
| [FMMS_Architecture.md](FMMS_Architecture.md) | System architecture, layer definitions, core domains, SOLID principles | All engineers |
| [Database_Design.md](Database_Design.md) | Database design rules, BaseModel fields, entity list, soft delete policy | Backend engineers |
| [SAP_Integration.md](SAP_Integration.md) | SAP ownership boundaries, read/write integrations, SAPTransaction requirements | Backend + Integration engineers |
| [API_Contract.md](API_Contract.md) | REST API principles, error format, security requirements, documentation standards | Backend + Frontend engineers |

---

## Development & Planning

| Document | Description | Audience |
|---|---|---|
| [IMPLEMENTATION_TRACKER.md](IMPLEMENTATION_TRACKER.md) | **Single source of truth** — milestone tasks, git history, ADR decision log | Lead engineer |
| [BRANCH_STRATEGY.md](BRANCH_STRATEGY.md) | Git branching model, merge rules, release process | All engineers |

---

## Cursor AI Rules

| File | Description |
|---|---|
| [../.cursor/rules/FMMS_Cursor_Rules_Backend_Architecture.mdc](../.cursor/rules/FMMS_Cursor_Rules_Backend_Architecture.mdc) | Mandatory coding rules applied to all generated Python code |

---

## Quick Reference

### Architecture Layer Responsibilities

| Layer | Location | Responsibility |
|---|---|---|
| Interface | `interfaces/api/v1/` | DRF views, serializers, URL routing |
| Application | `apps/<domain>/application/` | Services, use cases, DTOs |
| Domain | `apps/<domain>/domain/` | Entities, value objects, domain exceptions, repository interfaces |
| Infrastructure | `apps/<domain>/infrastructure/` + `infrastructure/` | ORM models, repositories, SAP adapters, Celery, Redis |

### SAP Port Interfaces

All SAP port interfaces live in `core/sap/ports/`. Application services import from here — never from `infrastructure/`.

| Port Interface | File | SAP API |
|---|---|---|
| `ISAPEquipmentPort` | `core/sap/ports/equipment_port.py` | `API_EQUIPMENT` |
| `ISAPObjectPartCatalogPort` | `core/sap/ports/object_part_catalog_port.py` | — |
| `ISAPFaultCatalogPort` | `core/sap/ports/fault_catalog_port.py` | `API_DEFECTCODE_SRV` |
| `ISAPMaterialPort` | `core/sap/ports/material_port.py` | `API_PRODUCT_SRV` |
| `ISAPInventoryPort` | `core/sap/ports/inventory_port.py` | `API_MATERIAL_STOCK_SRV` |
| `ISAPPMNotificationPort` | `core/sap/ports/pm_notification_port.py` | BAPI |
| `ISAPPMOrderPort` | `core/sap/ports/pm_order_port.py` | BAPI |
| `ISAPPurchaseRequisitionPort` | `core/sap/ports/purchase_requisition_port.py` | BAPI |
| `ISAPPurchaseOrderPort` | `core/sap/ports/purchase_order_port.py` | BAPI |
| `ISAPGoodsReceiptPort` | `core/sap/ports/goods_receipt_port.py` | BAPI |
| `ISAPGoodsIssuePort` | `core/sap/ports/goods_issue_port.py` | BAPI |
| `ISAPServicePOPort` | `core/sap/ports/service_po_port.py` | BAPI |

### Commit Format

```
type(scope): description

Types:   feat | fix | docs | chore | test | refactor | perf
Scopes:  core | domain | vehicle | driver | inspection | fault |
         repair | pm | procurement | sap | api | auth | infra | repo
```

### Key Decisions (ADR Summary)

| ADR | Decision |
|---|---|
| ADR-001 | Domain-per-app internal layering |
| ADR-002 | Shared SAP infrastructure at project level |
| ADR-003 | Abstract repository interfaces in domain layer |
| ADR-004 | `SAPTransactionManager` as sole SAP write gateway |
| ADR-005 | Settings split by environment |
| ADR-006 | Soft delete on all business records |
| ADR-007 | `SAPTransaction` uses generic relation (no FK) |
| ADR-008 | SAP port interfaces in `core/sap/ports/` |
| ADR-009 | Custom `FMMSUser` model before first migration |
| ADR-010 | Reporting domain deferred to Phase 2 |
| ADR-011 | `pyproject.toml` as single tool configuration |

Full ADR details: [IMPLEMENTATION_TRACKER.md — Decision Log](IMPLEMENTATION_TRACKER.md#decision-log)

---

## Phase Scope

| Phase | Domains | Status |
|---|---|---|
| Phase 1 | Vehicle, Driver, Inspection, Fault, Repair, PM, Procurement, Integration, Auth | Active — M0 to M10 |
| Phase 2 | Reporting | Planned |

---

*Last updated: 2026-07-09*
