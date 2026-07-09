# FMMS — Fleet Maintenance Management System

> Enterprise-grade backend for fleet maintenance operations.
> Acts as an operational layer between users and SAP.

---

## Overview

FMMS is a Django-based backend system that manages the full lifecycle of fleet
maintenance — from vehicle inspection and fault reporting through repair execution,
preventive maintenance scheduling, and procurement. All operational data flows
through FMMS while SAP remains the system of record for master data.

---

## Architecture

FMMS follows **Clean Architecture** with strict layer separation:

```
┌─────────────────────────────────┐
│        Interface Layer          │  REST API (DRF), Serializers
├─────────────────────────────────┤
│      Application Layer          │  Services, Use Cases, DTOs
├─────────────────────────────────┤
│        Domain Layer             │  Entities, Value Objects, Rules
├─────────────────────────────────┤
│     Infrastructure Layer        │  ORM, SAP Adapters, Redis, Celery
└─────────────────────────────────┘
```

### SAP Integration Flow

```
Application Service
    → core/sap/ports/          (abstract interface)
    → infrastructure/sap/adapters/    (concrete adapter)
    → infrastructure/sap/client/      (HTTP / RFC client)
    → SAP (OData / BAPI / RFC)
```

All SAP writes are gated through `SAPTransactionManager` — providing idempotency,
retry, and full audit trail via `SAPTransaction` records.

---

## Core Domains

| Domain                  | Responsibility                                       |
|-------------------------|------------------------------------------------------|
| Vehicle Management      | Vehicle registry, SAP equipment sync                 |
| Driver Management       | Driver profiles, vehicle assignments                 |
| Inspection              | Pre/post-trip inspections, checklist management      |
| Fault Management        | Fault reporting, severity classification, lifecycle  |
| Repair Management       | Repair orders, technician assignment, parts tracking |
| Preventive Maintenance  | PM plans, scheduled work orders, overdue triggers    |
| Procurement             | Purchase requisitions, orders, goods receipt/issue   |
| Integration             | SAP transaction tracking, sync status, retry logs    |

---

## Technology Stack

| Component       | Technology                          |
|-----------------|-------------------------------------|
| Language        | Python 3.12                         |
| Framework       | Django 5.x + Django REST Framework  |
| Database        | PostgreSQL 16                       |
| Cache / Broker  | Redis 7                             |
| Task Queue      | Celery + Celery Beat                |
| SAP Integration | OData (requests/httpx) + BAPI (pyrfc) |
| Auth            | JWT (djangorestframework-simplejwt) |
| API Docs        | drf-spectacular (OpenAPI 3.0)       |
| Code Quality    | black, isort, ruff, mypy            |
| Testing         | pytest, pytest-django, factory-boy  |
| Containerization| Docker + docker-compose             |

---

## Project Structure

```
FMMS/
├── config/                  # Django project settings (base, dev, staging, prod)
├── core/                    # Cross-cutting: logging, exceptions, middleware, SAP ports
│   ├── logging/
│   ├── exceptions/
│   ├── middleware/
│   ├── pagination/
│   ├── permissions/
│   └── sap/
│       └── ports/           # Abstract SAP port interfaces (ISAPEquipmentPort, etc.)
├── apps/                    # One Django app per domain
│   ├── authentication/      # Custom FMMSUser model, roles
│   ├── vehicle/
│   ├── driver/
│   ├── inspection/
│   ├── fault/
│   ├── repair/
│   ├── preventive_maintenance/
│   ├── procurement/
│   ├── integration/
│   └── reporting/           # Phase 2
├── infrastructure/          # Shared infrastructure
│   ├── database/            # BaseModel
│   ├── sap/                 # SAP clients + adapters + transaction manager
│   └── messaging/           # Celery app + tasks
├── interfaces/              # REST API (DRF views, serializers, URLs)
│   └── api/
│       └── v1/
├── tests/                   # All tests
│   ├── unit/
│   ├── integration/
│   └── factories/
├── docs/                    # Architecture and planning documents
└── prototypes/              # Exploratory code (not production)
```

Each domain app has its own internal Clean Architecture:
```
apps/<domain>/
    domain/          # Entities, value objects, exceptions, repository interfaces
    application/     # Services, DTOs
    infrastructure/  # ORM models, repository implementations, migrations
    interfaces/      # (thin — views handled in top-level interfaces/)
```

---

## Quick Start

### Prerequisites

- Docker and docker-compose
- Python 3.12 (for local development without Docker)
- `make`

### 1. Clone and configure

```bash
git clone <repo-url>
cd FMMS
cp .env.example .env
# Edit .env with your local values
```

### 2. Start with Docker

```bash
make run
```

This starts PostgreSQL, Redis, and the Django development server.

### 3. Apply migrations

```bash
make migrate
```

### 4. Run tests

```bash
make test
```

### 5. Run code quality checks

```bash
make lint
```

---

## Make Targets

| Target               | Description                                      |
|----------------------|--------------------------------------------------|
| `make run`           | Start all services via docker-compose            |
| `make test`          | Run full pytest suite with coverage              |
| `make lint`          | black + isort + ruff + mypy checks               |
| `make format`        | Auto-format with black + isort                   |
| `make migrate`       | Run Django database migrations                   |
| `make shell`         | Open Django shell                                |
| `make worker`        | Start Celery worker                              |
| `make beat`          | Start Celery beat scheduler                      |
| `make createsuperuser` | Create an admin user                           |

---

## API Documentation

Once running, the interactive API documentation is available at:

| URL                              | Description        |
|----------------------------------|--------------------|
| `/api/schema/swagger-ui/`        | Swagger UI         |
| `/api/schema/redoc/`             | Redoc              |
| `/api/schema/`                   | Raw OpenAPI JSON   |
| `/api/health/`                   | Health check       |

---

## Environment Variables

See `.env.example` for the full list of required variables with descriptions.

Key variables:

```env
DJANGO_SETTINGS_MODULE=config.settings.development
SECRET_KEY=<django-secret-key>
DATABASE_URL=postgres://user:password@localhost:5432/fmms
REDIS_URL=redis://localhost:6379/0
SAP_HOST=https://your-sap-host
SAP_CLIENT=100
SAP_USER=your-sap-user
SAP_PASSWORD=your-sap-password
```

---

## Git Workflow

### Branch Strategy

| Branch          | Purpose                                      |
|-----------------|----------------------------------------------|
| `main`          | Production-ready code only                   |
| `develop`       | Integration branch — all features merge here |
| `feat/*`        | Feature / milestone branches                 |
| `fix/*`         | Bug fix branches                             |
| `hotfix/*`      | Emergency production fixes                   |

See `docs/BRANCH_STRATEGY.md` for the full branching model.

### Commit Format

```
type(scope): description

Types:  feat | fix | docs | chore | test | refactor | perf
Scope:  core | domain | vehicle | driver | inspection | fault |
        repair | pm | procurement | sap | api | auth | infra | repo

Examples:
  feat(vehicle): implement create vehicle service
  feat(sap): add PM order BAPI adapter
  fix(repair): handle invalid state transition error
  test(vehicle): add unit tests for create vehicle service
  docs(api): update API contract documentation
  chore(repo): initialize FMMS repository
```

---

## Development Roadmap

| Milestone | Description                                   | Status    |
|-----------|-----------------------------------------------|-----------|
| M0        | Repository initialization                     | In Progress |
| M1        | Project foundation (Django, config, logging)  | Pending   |
| M2        | Domain layer (entities, value objects)        | Pending   |
| M3        | Infrastructure — ORM models & repositories   | Pending   |
| M4        | SAP integration layer                         | Pending   |
| M5        | Application services — core domains           | Pending   |
| M6        | Application services — maintenance domains    | Pending   |
| M7        | REST API v1                                   | Pending   |
| M8        | Async background tasks (Celery)               | Pending   |
| M9        | Testing completeness & coverage               | Pending   |
| M10       | Hardening & documentation                     | Pending   |

See `docs/IMPLEMENTATION_TRACKER.md` for detailed task lists and progress.

---

## Documentation

| Document                              | Description                              |
|---------------------------------------|------------------------------------------|
| `docs/FMMS_Architecture.md`          | Architecture principles and layer design |
| `docs/Database_Design.md`            | Database schema and design rules         |
| `docs/SAP_Integration.md`            | SAP integration architecture             |
| `docs/API_Contract.md`               | API design principles and error format   |
| `docs/IMPLEMENTATION_TRACKER.md`     | Milestone tracker and decision log       |
| `docs/BRANCH_STRATEGY.md`            | Git branching model                      |
| `docs/index.md`                      | Documentation index                      |

---

## Code Quality Standards

- **Architecture:** Clean Architecture — zero business logic in controllers
- **Style:** PEP8, enforced by `black` and `isort`
- **Linting:** `ruff` — no warnings tolerated
- **Types:** `mypy` strict mode — every function must have type hints
- **Docs:** Google Style Docstrings on every public class, method, and function
- **Logging:** Structured JSON logging — `print()` is forbidden
- **Tests:** Minimum 80% coverage — domain logic testable without database

---

*FMMS — Built for long-term enterprise maintainability.*
