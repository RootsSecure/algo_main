# Edge Device App Integration Prompt

Use this prompt when you want another app, agent, or frontend builder to create an edge-device client against this backend.

```text
Build a secure edge-device client integration for the NRI Plot Sentinel backend.

Requirements:
- The client may run on a Raspberry Pi, a normal PC, or another edge device connected to a camera.
- Use the dedicated gateway endpoints, not the normal owner login endpoints.
- Bootstrap with POST /api/v1/gateway/raspberry-pi/connect using a provisioning bearer token.
- After connect succeeds, store the returned session token securely and use it for:
  - POST /api/v1/gateway/raspberry-pi/devices/{device_id}/heartbeat
  - POST /api/v1/gateway/raspberry-pi/devices/{device_id}/events
- Include a stable hardware_id in the connect payload.
- Reconnect automatically when the session token expires or the API returns 401.
- Maintain a local retry queue for events when connectivity is temporarily unavailable.
- Send heartbeat updates on a fixed interval with network status, power status, battery level, and metadata.
- Normalize camera-side detections into the backend event schema with alert_type, vendor_event_id, occurred_at, metadata_json, and media_refs.
- Treat the provisioning token as bootstrap-only and avoid using it for normal event traffic after a session token is issued.
- Keep the implementation modular so camera capture, event classification, token management, and API transport are separate components.
- Prefer HTTPS requests, request timeouts, structured logging, and clear reconnect behavior.
- Make the client code beginner friendly with clear comments, small modules, and a short README.

Deliverables:
- A client service module for token bootstrap and reconnect
- A heartbeat sender
- An event uploader
- A local event queue for offline buffering
- A concise README explaining setup, config, and how to register the device with the backend
```
