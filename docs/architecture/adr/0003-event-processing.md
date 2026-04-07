# ADR 0003: Synchronous Request Path with Service Abstractions

## Status
Accepted

## Context
The MVP needs to be understandable and testable before introducing queues or worker orchestration.

## Decision
Keep the request path synchronous for core flows, but isolate behavior in services so background processing can be introduced later.

## Consequences
- Fewer moving parts in v1
- Easier test setup
- Straightforward future extraction of alert processing into job workers
