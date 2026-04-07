# Webhook and Vendor Event Contract

## Purpose

The MVP expects vendor hardware or adapter services to convert source-specific payloads into the normalized alert ingestion contract.

## Required normalized fields

- `property_id`
- `alert_type`

## Optional fields

- `device_id`
- `vendor_event_id`
- `occurred_at`
- `metadata_json`
- `media_refs`

## Example normalized payload

```json
{
  "property_id": 12,
  "device_id": 44,
  "alert_type": "tamper",
  "vendor_event_id": "evt-92",
  "occurred_at": "2026-04-08T12:30:00Z",
  "metadata_json": {"signal": "camera_shake"},
  "media_refs": ["evidence://clip-92"]
}
```

## Adapter expectations

- Map vendor-specific event names to supported alert types
- Preserve the original vendor event id when available
- Attach references to media clips without forcing raw file upload through the API
- Avoid sending duplicate alerts if vendor retries can be coalesced upstream
