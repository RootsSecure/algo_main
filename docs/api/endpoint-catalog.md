# Endpoint Catalog

## Auth

- `POST /api/v1/auth/register-owner`: create an owner account
- `POST /api/v1/auth/login`: obtain access and refresh tokens
- `POST /api/v1/auth/refresh`: exchange refresh token for new tokens
- `POST /api/v1/auth/invite-delegate`: create or refresh delegate invite
- `POST /api/v1/auth/accept-invite`: activate delegate account
- `GET /api/v1/auth/me`: inspect current authenticated user

## Properties

- `POST /api/v1/properties`: create property
- `GET /api/v1/properties`: list accessible properties
- `GET /api/v1/properties/{property_id}`: retrieve property detail
- `PATCH /api/v1/properties/{property_id}`: update property metadata
- `POST /api/v1/properties/{property_id}/zones`: add a monitoring zone
- `POST /api/v1/properties/{property_id}/delegates/{delegate_user_id}`: assign an invited delegate

## Devices

- `POST /api/v1/devices`: register device
- `GET /api/v1/devices`: list devices, optional `property_id`
- `POST /api/v1/devices/{device_id}/heartbeat`: record heartbeat and health note

## Gateway

- `POST /api/v1/gateway/devices/{device_id}/provision`: issue Raspberry Pi provisioning token
- `POST /api/v1/gateway/raspberry-pi/connect`: exchange provisioning token for a session token
- `POST /api/v1/gateway/raspberry-pi/devices/{device_id}/heartbeat`: submit Raspberry Pi heartbeat
- `POST /api/v1/gateway/raspberry-pi/devices/{device_id}/events`: submit Raspberry Pi-generated event

## Alerts

- `POST /api/v1/alerts/ingest`: ingest normalized alert
- `GET /api/v1/alerts`: list alerts with optional filters

## Incidents

- `GET /api/v1/incidents`: list incidents
- `POST /api/v1/incidents/{incident_id}/verify`: verify or dismiss incident
- `POST /api/v1/incidents/{incident_id}/evidence`: attach evidence metadata
- `POST /api/v1/incidents/{incident_id}/dispatch`: create partner dispatch
- `PATCH /api/v1/incidents/dispatches/{dispatch_id}`: update dispatch status
- `PATCH /api/v1/incidents/{incident_id}/status`: set incident status directly
- `GET /api/v1/incidents/{incident_id}/export-summary`: export structured summary

## Health

- `GET /api/v1/health/properties/{property_id}`: property health summary
- `GET /api/v1/health/devices`: device health summaries
- `GET /api/v1/health/devices/offline`: stale or offline devices

## Partners

- `POST /api/v1/partners`: create partner
- `GET /api/v1/partners`: list partners
