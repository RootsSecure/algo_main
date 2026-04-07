def test_delegate_invite_assignment_and_health_views(client, auth_headers) -> None:
    owner_headers = auth_headers()

    property_response = client.post(
        "/api/v1/properties",
        json={
            "name": "Open Plot",
            "address": "Survey No. 42",
            "city": "Indore",
            "state": "Madhya Pradesh",
            "country": "India",
            "geo_boundary": {"type": "Polygon", "coordinates": []},
            "site_type": "open_plot",
            "risk_profile": {"encroachment_risk": "medium"},
            "escalation_plan": {"critical": ["owner"]},
        },
        headers=owner_headers,
    )
    property_id = property_response.json()["id"]

    invite_response = client.post(
        "/api/v1/auth/invite-delegate",
        json={"full_name": "Trusted Cousin", "email": "delegate@example.com"},
        headers=owner_headers,
    )
    assert invite_response.status_code == 200, invite_response.text
    invite_token = invite_response.json()["message"].split("invite_token=")[1]

    accept_response = client.post(
        "/api/v1/auth/accept-invite",
        json={"invite_token": invite_token, "password": "DelegatePass123!"},
    )
    assert accept_response.status_code == 200, accept_response.text
    delegate_user_id = accept_response.json()["user_id"]

    assign_response = client.post(
        f"/api/v1/properties/{property_id}/delegates/{delegate_user_id}",
        headers=owner_headers,
    )
    assert assign_response.status_code == 200, assign_response.text

    delegate_headers = auth_headers("delegate@example.com", "DelegatePass123!")
    delegated_property_response = client.get(f"/api/v1/properties/{property_id}", headers=delegate_headers)
    assert delegated_property_response.status_code == 200, delegated_property_response.text

    health_response = client.get(f"/api/v1/health/properties/{property_id}", headers=owner_headers)
    assert health_response.status_code == 200, health_response.text
    assert health_response.json()["device_count"] == 0
