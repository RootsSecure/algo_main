from __future__ import annotations

from datetime import UTC, datetime


def test_owner_property_device_alert_incident_flow(client, auth_headers) -> None:
    headers = auth_headers()

    property_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Family Plot in Jaipur",
            "address": "Plot 18, Sector 4",
            "city": "Jaipur",
            "state": "Rajasthan",
            "country": "India",
            "postal_code": "302001",
            "geo_boundary": {"type": "Polygon", "coordinates": [[[75.8, 26.9], [75.81, 26.9], [75.81, 26.91], [75.8, 26.9]]]},
            "site_type": "walled_plot",
            "risk_profile": {"encroachment_risk": "high"},
            "escalation_plan": {"critical": ["ops", "partner", "owner"]},
        },
        headers=headers,
    )
    assert property_response.status_code == 200, property_response.text
    property_id = property_response.json()["id"]

    zone_response = client.post(
        f"/api/v1/properties/{property_id}/zones",
        json={
            "name": "North Gate",
            "zone_type": "entry",
            "polygon": {"coordinates": [[1, 1], [2, 2]]},
            "allowed_activity_window": {"start": "09:00", "end": "18:00"},
            "sensitivity_level": "high",
        },
        headers=headers,
    )
    assert zone_response.status_code == 200, zone_response.text

    device_response = client.post(
        "/api/v1/devices",
        json={
            "property_id": property_id,
            "vendor": "SolarCam",
            "device_type": "camera",
            "serial_number": "SOL-001",
            "install_location": "Main gate pole",
            "power_status": "healthy",
            "network_status": "online",
            "battery_level": 89,
            "metadata_json": {"lte": True},
        },
        headers=headers,
    )
    assert device_response.status_code == 200, device_response.text
    device_id = device_response.json()["id"]

    heartbeat_response = client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={"power_status": "healthy", "network_status": "online", "battery_level": 87, "metadata_json": {"signal": "strong"}},
        headers=headers,
    )
    assert heartbeat_response.status_code == 200, heartbeat_response.text

    alert_response = client.post(
        "/api/v1/alerts/ingest",
        json={
            "property_id": property_id,
            "device_id": device_id,
            "alert_type": "tamper",
            "vendor_event_id": "evt-1",
            "occurred_at": datetime.now(UTC).isoformat(),
            "metadata_json": {"trigger": "camera_shake"},
            "media_refs": ["evidence://clip-1"],
        },
        headers=headers,
    )
    assert alert_response.status_code == 200, alert_response.text
    alert_payload = alert_response.json()
    assert alert_payload["severity"] == "critical"
    incident_id = alert_payload["incident_id"]

    incidents_response = client.get(f"/api/v1/incidents?property_id={property_id}", headers=headers)
    assert incidents_response.status_code == 200, incidents_response.text
    assert len(incidents_response.json()) == 1

    partner_response = client.post(
        "/api/v1/partners",
        json={
            "name": "Jaipur Field Team",
            "service_area": "Jaipur North",
            "phone": "+91-9000000001",
            "email": "field@example.com",
        },
        headers=headers,
    )
    assert partner_response.status_code == 200, partner_response.text
    partner_id = partner_response.json()["id"]

    verify_response = client.post(
        f"/api/v1/incidents/{incident_id}/verify",
        json={"verification_status": "ops_verified"},
        headers=headers,
    )
    assert verify_response.status_code == 200, verify_response.text
    assert verify_response.json()["status"] == "verified"

    dispatch_response = client.post(
        f"/api/v1/incidents/{incident_id}/dispatch",
        json={"partner_id": partner_id, "eta_minutes": 15},
        headers=headers,
    )
    assert dispatch_response.status_code == 200, dispatch_response.text
    dispatch_id = dispatch_response.json()["id"]

    close_response = client.patch(
        f"/api/v1/incidents/dispatches/{dispatch_id}",
        json={"status": "closed", "closure_notes": "Site secured", "proof_refs": ["proof://arrival-photo"]},
        headers=headers,
    )
    assert close_response.status_code == 200, close_response.text

    summary_response = client.get(f"/api/v1/incidents/{incident_id}/export-summary", headers=headers)
    assert summary_response.status_code == 200, summary_response.text
    summary = summary_response.json()
    assert summary["incident_id"] == incident_id
    assert summary["dispatches"][0]["dispatch_id"] == dispatch_id
