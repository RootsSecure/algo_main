from datetime import UTC, datetime

from sentinel_edge.network.api_client import normalize_edge_event, serialize_occurred_at


def test_normalize_edge_event_maps_illegal_construction_to_manual_report() -> None:
    alert_type, metadata = normalize_edge_event("ILLEGAL_CONSTRUCTION", {"reason": "JCB detected"})
    assert alert_type == "manual_report"
    assert metadata["edge_event_type"] == "ILLEGAL_CONSTRUCTION"
    assert metadata["recommended_severity"] == "critical"


def test_serialize_occurred_at_supports_timestamps() -> None:
    value = serialize_occurred_at(1_760_000_000)
    assert "T" in value


def test_serialize_occurred_at_supports_datetime() -> None:
    instant = datetime.now(UTC)
    assert serialize_occurred_at(instant).startswith(str(instant.year))
