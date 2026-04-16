from enum import Enum


class Role(str, Enum):
    OWNER = "owner"
    DELEGATE = "delegate"
    INSTALLER = "installer"
    PARTNER = "partner"
    OPS_ADMIN = "ops_admin"


class SiteType(str, Enum):
    WALLED_PLOT = "walled_plot"
    PARTIALLY_FENCED_PLOT = "partially_fenced_plot"
    OPEN_PLOT = "open_plot"


class DeviceType(str, Enum):
    CAMERA = "camera"
    TAMPER_SENSOR = "tamper_sensor"
    GATE_SENSOR = "gate_sensor"
    SIREN = "siren"
    SMART_LOCK = "smart_lock"


class EventType(str, Enum):
    MOTION = "motion"
    TAMPER = "tamper"
    OFFLINE = "offline"
    GATE_BREACH = "gate_breach"
    MANUAL_REPORT = "manual_report"
    HEARTBEAT = "heartbeat"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class VerificationStatus(str, Enum):
    PENDING = "pending"
    AUTO_VERIFIED = "auto_verified"
    OPS_VERIFIED = "ops_verified"
    DISMISSED = "dismissed"


class IncidentStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    DISPATCHED = "dispatched"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class DispatchStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EN_ROUTE = "en_route"
    ARRIVED = "arrived"
    CLOSED = "closed"


class NotificationChannel(str, Enum):
    PUSH = "push"
    WHATSAPP = "whatsapp"
    SMS = "sms"


class NotificationStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"

