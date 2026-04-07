# NRI Plot Sentinel

NRI Plot Sentinel is a backend-first MVP for remotely securing vacant land plots owned by NRIs. The project focuses on detecting unauthorized entry, encroachment risk, suspicious construction activity, device tampering, and site-health failures, then escalating verified incidents to owners and response partners with a documented workflow.

## Beginner-friendly quick start

If you are new to the project, follow this order:

1. Read `docs/getting-started.md`
2. Read `docs/README.md`
3. Run the setup commands below
4. Run the tests
5. Open `/docs` and `/project-docs`

## What is in this repository

- FastAPI backend under `app/`
- Alembic migration setup under `alembic/`
- Layered tests under `tests/`
- Detailed documentation under `docs/`
- A virtual-environment-friendly task runner in `manage.py`
- A contribution guide in `CONTRIBUTING.md`

## Core product capabilities in v1

- Owner authentication with JWT access and refresh tokens
- Delegate invitation and acceptance workflow
- Vacant plot onboarding with geo-boundary, site type, and escalation plan
- Zone creation for gates, edges, blind spots, and sensitive areas
- Device registration and heartbeat tracking
- Unified alert ingestion for motion, tamper, offline, gate breach, and manual reports
- Incident creation, verification, evidence attachment, partner dispatch, and export summary
- Property and device health endpoints
- Secure edge-device gateway for Raspberry Pi or normal PC based camera agents
- Project documentation index route at `/project-docs`

## Local setup inside `nri_proj`

1. Create the environment:
   `py -m venv nri_proj`
2. Activate it in PowerShell:
   `.\nri_proj\Scripts\Activate.ps1`
3. Install dependencies:
   `python -m pip install -r requirements.txt`
4. Copy the environment template:
   `Copy-Item .env.example .env`
5. Apply migrations:
   `python -B -m alembic upgrade head`
6. Start the API:
   `python manage.py run`

## Local commands

- Run migrations: `python manage.py migrate`
- Run tests: `python manage.py test`
- Start dev server: `python manage.py run`

All commands assume the shell is already inside the `nri_proj` virtual environment. The `manage.py` runner also uses the active interpreter directly to avoid accidentally invoking global Python tools.

## How the project is organized

- `app/core`: settings, DB wiring, auth utilities, dependency helpers
- `app/models`: SQLAlchemy models and base classes
- `app/repos`: repository helpers for reusable queries
- `app/services`: domain workflows for auth, properties, alerts, incidents, health, notifications, gateway access, and bootstrap
- `app/api/v1/endpoints`: HTTP routes grouped by domain
- `docs/product`: product vision, PRD, personas, journeys, roadmap
- `docs/architecture`: architecture, event flow, domain model, ADRs, security
- `docs/api`: endpoint catalog, auth rules, error model, webhook contracts, edge-device gateway contract
- `docs/ops`: incident triage and dispatch procedures
- `docs/field`: installer assumptions and plot deployment guidance
- `docs/qa`: test strategy and validation guides
- `docs/support`: onboarding, alert glossary, FAQ, troubleshooting, and app prompts

## API documentation

- OpenAPI UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- In-app project docs index: `http://127.0.0.1:8000/project-docs`

## Default development users

The app seeds two users when the schema exists and the records are missing:

- Owner: `owner@example.com` / `ChangeMe123!`
- Ops admin: `ops@example.com` / `ChangeMe123!`

Change these immediately in `.env` for any environment beyond local development.

## Edge-device gateway

A dedicated hardware gateway is available for Raspberry Pi, normal PC, or other small edge devices running the camera or sensor agent.

Flow:
1. Owner or ops provisions a specific registered device through the gateway provision endpoint.
2. The edge device connects with the provisioning token.
3. Backend returns a short-lived session token.
4. The edge device uses the session token for heartbeats and event uploads.

See `docs/api/raspberry-pi-gateway.md` and `docs/support/raspberry-pi-app-prompt.md` for the full connection contract and app-building prompt.

## Release discipline

A feature is not complete until all of the following are updated:

- The relevant product spec in `docs/product`
- The technical or API contract in `docs/api` or `docs/architecture`
- The operational workflow in `docs/ops`
- The owner-facing help content in `docs/support`

## Current implementation limits

- SQLite is the default local database; PostgreSQL is the intended production database later
- Notification delivery is mocked through persistent notification logs, not live provider calls
- Raw media storage is represented by evidence metadata and storage references, not a production media pipeline
- Vendor integrations use a normalized event contract rather than vendor-specific SDK lock-in
- This repository is backend-first; a dedicated owner mobile app and partner app are future steps
