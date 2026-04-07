from __future__ import annotations

from datetime import UTC, datetime


def test_raspberry_pi_gateway_provision_connect_and_event_flow(client, auth_headers) -> None:
    headers = auth_headers()

    property_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Gateway Plot",
            "address": "Plot 52, Ring Road",
            "city": "Lucknow",
            "state": "Uttar Pradesh",
            "country": "India",
            "geo_boundary": {"type": "Polygon", "coordinates": []},
            "site_type": "walled_plot",
            "risk_profile": {"encroachment_risk": "high"},
            "escalation_plan": {"critical": ["owner", "ops"]},
        },
        headers=headers,
    )
    property_id = property_response.json()["id"]

    device_response = client.post(
        "/api/v1/devices",
        json={
            "property_id": property_id,
            "vendor": "Raspberry Pi",
            "device_type": "camera",
            "serial_number": "RPI-CAM-01",
            "install_location": "Boundary pole east",
            "power_status": "healthy",
            "network_status": "online",
            "battery_level": 100,
            "metadata_json": {"camera": "Pi Camera Module 3"},
        },
        headers=headers,
    )
    assert device_response.status_code == 200, device_response.text
    device_id = device_response.json()["id"]

    provision_response = client.post(
        f"/api/v1/gateway/devices/{device_id}/provision",
        json={"hardware_id": "rpi-plot-east-001"},
        headers=headers,
    )
    assert provision_response.status_code == 200, provision_response.text
    provisioning_token = provision_response.json()["provisioning_token"]

    gateway_auth = {"Authorization": f"Bearer {provisioning_token}"}
    connect_response = client.post(
        "/api/v1/gateway/raspberry-pi/connect",
        json={
            "hardware_id": "rpi-plot-east-001",
            "network_status": "online",
            "power_status": "healthy",
            "battery_level": 97,
            "ip_address": "10.0.0.24",
            "client_version": "sentinel-pi-0.1.0",
            "camera_model": "Pi Camera Module 3",
            "metadata_json": {"stream_profile": "1080p-low-latency"},
        },
        headers=gateway_auth,
    )
    assert connect_response.status_code == 200, connect_response.text
    session_token = connect_response.json()["session_token"]

    session_headers = {"Authorization": f"Bearer {session_token}"}
    heartbeat_response = client.post(
        f"/api/v1/gateway/raspberry-pi/devices/{device_id}/heartbeat",
        json={
            "network_status": "online",
            "power_status": "healthy",
            "battery_level": 95,
            "ip_address": "10.0.0.24",
            "metadata_json": {"temperature_c": 42},
        },
        headers=session_headers,
    )
    assert heartbeat_response.status_code == 200, heartbeat_response.text
    assert heartbeat_response.json()["gateway_enabled"] is True

    event_response = client.post(
        f"/api/v1/gateway/raspberry-pi/devices/{device_id}/events",
        json={
            "alert_type": "tamper",
            "vendor_event_id": "pi-event-1",
            "occurred_at": datetime.now(UTC).isoformat(),
            "metadata_json": {"sensor": "camera_shake"},
            "media_refs": ["pi://clips/clip-1.mp4"],
        },
        headers=session_headers,
    )
    assert event_response.status_code == 200, event_response.text
    payload = event_response.json()
    assert payload["severity"] == "critical"
    assert payload["incident_id"] is not None
