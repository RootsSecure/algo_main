# Product Requirements Document

## Product name

NRI Plot Sentinel

## Target customer

Primary: NRI individual landowners protecting vacant plots in India.

Secondary later: family delegates, local caretakers, and professional property managers.

## MVP objective

Ship a backend foundation that supports end-to-end vacant-plot monitoring workflows: onboarding, device registration, alert ingestion, incident creation, verification, dispatch, health monitoring, and evidence export.

## MVP functional requirements

1. Auth and access
- Register owners
- Log in with access and refresh tokens
- Invite delegates
- Accept delegate invites
- Enforce role-aware access

2. Property management
- Create properties with location and site metadata
- Define site type and risk profile
- Create monitoring zones
- Assign delegates to a property

3. Device operations
- Register devices against a property
- Track install location, power, network, and battery state
- Record heartbeats
- Surface stale or offline devices

4. Alert and incident pipeline
- Ingest normalized device or manual alerts
- Classify severity
- Open or enrich incidents
- Track verification status
- Support evidence attachment and export

5. Response workflow
- Create and manage response partners
- Dispatch a partner to a verified incident
- Track arrival and closure notes
- Resolve incidents with structured outcomes

6. Documentation and readiness
- Provide OpenAPI docs and in-app project docs index
- Maintain product, technical, ops, field, QA, and support documentation in-repo

## Non-functional requirements

- Clear separation of API, services, models, and repositories
- Migration-controlled schema changes
- Adapter-ready notification abstraction
- Compatibility with later PostgreSQL adoption
- Test coverage for core incident and auth workflows

## Out of scope for v1

- Real hardware provisioning
- Live WhatsApp/SMS provider integration
- Computer vision models beyond normalized alert ingestion
- Legal filing automation
- Owner mobile app UI beyond the API and docs layer
