# Alert Triage SOP

## Objective

Give operations users a repeatable path for deciding whether an incoming alert represents noise, a health issue, or a real plot-security incident.

## Triage order

1. Confirm the property and device involved.
2. Check the alert type and severity.
3. Review recent alerts for the same property.
4. Check whether device health is degraded.
5. Review media references or related evidence.
6. Decide whether to dismiss, monitor, verify, or dispatch.

## Default interpretations

- Tamper: treat as urgent and suspicious unless disproven
- Gate breach: treat as urgent and suspicious
- Motion: contextual; repeated motion raises concern
- Offline: investigate coverage impact and timing
- Manual report: confirm source credibility and attach supporting notes

## Required logging behavior

- Verification decisions must be reflected in incident status
- Incident closures must include a resolution code or closure notes
- Evidence additions should happen before final closure when material exists
