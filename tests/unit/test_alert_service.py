from app.core.enums import EventType, Severity
from app.schemas.alert import AlertIngest
from app.services.alert_service import AlertService


def test_classify_tamper_as_critical() -> None:
    service = AlertService()
    payload = AlertIngest(property_id=1, alert_type=EventType.TAMPER)
    assert service.classify_severity(payload, recent_alert_count=0) == Severity.CRITICAL


def test_classify_repeated_motion_as_critical() -> None:
    service = AlertService()
    payload = AlertIngest(property_id=1, alert_type=EventType.MOTION)
    assert service.classify_severity(payload, recent_alert_count=2) == Severity.CRITICAL


def test_classify_offline_as_warning() -> None:
    service = AlertService()
    payload = AlertIngest(property_id=1, alert_type=EventType.OFFLINE)
    assert service.classify_severity(payload, recent_alert_count=0) == Severity.WARNING
