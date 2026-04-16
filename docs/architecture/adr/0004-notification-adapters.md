# ADR 0004: Notification Adapters Log Intent Before Real Delivery

## Status
Accepted

## Context
The MVP needs a place for notifications in the incident workflow, but live provider integration would slow initial delivery.

## Decision
Represent notification delivery through adapter-friendly logs in the database first.

## Consequences
- Incident workflows can be tested now
- Delivery channels are visible in persistent records
- Real providers can replace the mock path later with minimal route changes
