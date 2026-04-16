# Event Flow

## Alert to incident sequence

```mermaid
sequenceDiagram
    participant D as Device or Manual Source
    participant A as Alert API
    participant S as Alert Service
    participant I as Incident Service
    participant N as Notification Service
    participant O as Owner or Ops

    D->>A: POST normalized alert
    A->>S: Validate and persist alert
    S->>S: Classify severity
    S->>I: Create or update incident
    I-->>S: Incident id and status
    alt Critical severity
        I->>N: Queue owner notifications
        N-->>O: Push/WhatsApp/SMS intent
    end
    S-->>A: Alert with incident link
    A-->>D: Accepted response
```

## Dispatch sequence

```mermaid
sequenceDiagram
    participant O as Ops or Owner
    participant I as Incident API
    participant S as Incident Service
    participant P as Partner

    O->>I: Verify incident
    I->>S: Update verification state
    O->>I: Dispatch partner
    I->>S: Create dispatch record
    S-->>P: Field task available
    P->>I: Update arrival and closure
    I->>S: Resolve incident when closed
```

## Rules summary

- Tamper and gate breach default to critical.
- Repeated motion can escalate to critical.
- Offline events default to warning.
- Critical incidents auto-queue notifications.
- Resolution and dispatch updates always create audit logs.
