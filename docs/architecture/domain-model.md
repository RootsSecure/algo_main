# Domain Model

## Core entities

### User
Represents owners, delegates, installers, partners, and ops admins. Users authenticate, access resources, and appear in audit logs.

### Property
Represents a monitored vacant plot. Holds address data, geo-boundary metadata, risk profile, site type, and escalation plan.

### Zone
Represents a meaningful region inside a plot such as a gate, wall edge, entry lane, or blind spot.

### Device
Represents a registered monitoring or control device. Stores vendor metadata, heartbeat state, install location, and battery/network context.

### Alert
Represents a normalized incoming security or health event. Alerts carry severity, vendor event identity, media references, and optional device linkage.

### Incident
Represents the operational unit of response. An incident groups alerts and tracks status, verification, assignment, dispatch timing, and resolution.

### Evidence
Represents structured evidence metadata tied to an incident, including storage reference, checksum, and retention policy.

### Partner
Represents a response partner or field team.

### PartnerDispatch
Represents an incident-specific field dispatch and its arrival/closure trail.

### SiteHealthCheck
Represents a generated site-health observation such as a heartbeat success or warning.

### NotificationLog
Represents intended outbound owner communication across channels.

### AuditLog
Represents a durable log of important state changes.

## Relationship notes

- One owner can own many properties.
- A property can have many delegates.
- A property can have many zones and devices.
- A property can produce many alerts and incidents.
- An incident can have many evidences and dispatches.
