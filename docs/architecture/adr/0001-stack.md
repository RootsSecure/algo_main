# ADR 0001: FastAPI and Layered Python Stack

## Status
Accepted

## Context
The project needs a backend-first MVP that can be built entirely inside a Python virtual environment, with strong API ergonomics, good documentation support, and clean migration to a richer production architecture later.

## Decision
Use FastAPI, SQLAlchemy 2, Alembic, and Pydantic v2 in a layered project structure.

## Consequences
- Fast API documentation comes for free
- Typed schemas stay close to route contracts
- Business logic can live in services instead of HTTP handlers
- We avoid over-investing in front-end code before the workflow is validated
