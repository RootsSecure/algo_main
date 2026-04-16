# User Journeys

## Journey 1: Owner onboards a new vacant plot

1. Owner authenticates.
2. Owner creates a property with address, site type, and geo-boundary.
3. Owner defines the escalation plan.
4. Installer or ops registers devices.
5. Heartbeats confirm the site is visible.
6. Owner checks the dashboard or API to confirm readiness.

## Journey 2: Suspicious activity is detected

1. A device or manual source sends an alert.
2. The alert is normalized and severity is assigned.
3. The system opens or enriches an incident.
4. If severity is critical, owner-facing notifications are logged and queued.
5. Ops or owner verifies the incident.
6. A partner dispatch can be created if field response is needed.
7. Evidence and closure proof are attached before final resolution.

## Journey 3: Delegate supports a remote owner

1. Owner invites a delegate.
2. Delegate accepts the invite and activates access.
3. Owner assigns the delegate to one or more properties.
4. Delegate can view the property, health status, incidents, and summaries.

## Journey 4: Site health silently degrades

1. Device heartbeat stops or network degrades.
2. Device health endpoint flags the device as stale or offline.
3. Site health summary reflects reduced coverage confidence.
4. Ops or owner can act before a real intrusion occurs during a blind spot.
