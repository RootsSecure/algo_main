# Manual Validation Guide

## Suggested local walkthrough

1. Activate `nri_proj`.
2. Apply migrations.
3. Start the API.
4. Log in with the default seeded owner.
5. Create a property.
6. Add at least one zone.
7. Register a device.
8. Post a heartbeat.
9. Ingest a tamper alert.
10. Verify the incident.
11. Create a partner and dispatch it.
12. Close the dispatch and export the incident summary.
13. Browse `/project-docs` and confirm documentation is visible.

## What to confirm manually

- statuses change as expected
- incident links are created automatically
- access control blocks unauthenticated requests
- health endpoints reflect current state
- documentation index resolves markdown files correctly
