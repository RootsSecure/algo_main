# ADR 0002: SQLite for Local Development, PostgreSQL Later

## Status
Accepted

## Context
The MVP should be simple to run inside `nri_proj` without external infrastructure.

## Decision
Use SQLite as the default local database and keep schema choices compatible with PostgreSQL.

## Consequences
- Local onboarding is easier
- Migration discipline still exists through Alembic
- Production rollout can move to PostgreSQL without redesigning the model layer
- Certain production concerns such as concurrent write behavior remain future work
