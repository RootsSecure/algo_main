from __future__ import annotations

import logging
import os
import socket
import queue
import threading
from datetime import UTC, datetime
from typing import Any

import requests

EDGE_ALERT_MAP = {
    "ILLEGAL_CONSTRUCTION": ("manual_report", "critical"),
    "SOIL_THEFT_ACTIVE": ("manual_report", "warning"),
    "SOIL_THEFT_ESCALATION": ("manual_report", "critical"),
}


def normalize_edge_event(alert_type: str, metadata_json: dict[str, Any] | None = None) -> tuple[str, dict[str, Any]]:
    metadata = dict(metadata_json or {})
    normalized_type, recommended_severity = EDGE_ALERT_MAP.get(
        alert_type,
        (str(alert_type).lower(), metadata.get("recommended_severity")),
    )
    if normalized_type not in {"motion", "tamper", "offline", "gate_breach", "manual_report"}:
        normalized_type = "manual_report"
    metadata.setdefault("edge_event_type", alert_type)
    if recommended_severity:
        metadata["recommended_severity"] = str(recommended_severity).lower()
    return normalized_type, metadata


def serialize_occurred_at(value: Any) -> str:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC).isoformat()
    if isinstance(value, str) and value.strip():
        return value
    return datetime.now(UTC).isoformat()


class SentinelAPIClient:
    def __init__(
        self,
        base_url: str,
        bootstrap_token: str,
        *,
        hardware_id: str | None = None,
        client_version: str = "sentinel-edge-0.2.0",
        camera_model: str | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.bootstrap_token = bootstrap_token
        self.session_token: str | None = None
        self.device_id: int | None = None
        self.property_id: int | None = None
        self.heartbeat_endpoint: str | None = None
        self.event_endpoint: str | None = None
        self.session = requests.Session()
        self.connected = False
        self.hardware_id = hardware_id or socket.gethostname()
        self.client_version = client_version
        self.camera_model = camera_model or "unknown-camera"
        
        # Async Network Pipeline
        self._work_queue: queue.Queue[tuple[str, dict[str, Any]]] = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def _worker_loop(self) -> None:
        """Drains the queue and executes HTTP POST requests synchronously without blocking the main loop."""
        while True:
            try:
                task = self._work_queue.get()
                if task is None:
                    break
                url, payload = task
                self._post_with_reconnect(url, payload)
                self._work_queue.task_done()
            except Exception as exc:
                logging.error("Background API worker encountered an error: %s", exc)

    def _headers(self, *, use_session: bool = True) -> dict[str, str]:
        token = self.session_token if use_session and self.session_token else self.bootstrap_token
        if not token:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }

    def _resolve_url(self, path: str | None, fallback_path: str) -> str:
        raw = path or fallback_path
        if raw.startswith("http://") or raw.startswith("https://"):
            return raw
        if not raw.startswith("/"):
            raw = f"/{raw}"
        return f"{self.base_url}{raw}"

    def connect(
        self,
        *,
        network_status: str = "online",
        power_status: str = "healthy",
        battery_level: int | None = None,
        ip_address: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> bool:
        """Bootstrap the connection and get a session token."""
        url = f"{self.base_url}/api/v1/gateway/raspberry-pi/connect"
        payload = {
            "hardware_id": self.hardware_id,
            "network_status": network_status,
            "power_status": power_status,
            "battery_level": battery_level,
            "ip_address": ip_address,
            "client_version": self.client_version,
            "camera_model": self.camera_model,
            "metadata_json": metadata_json or {},
        }
        try:
            response = self.session.post(url, json=payload, headers=self._headers(use_session=False), timeout=10)
            response.raise_for_status()
            data = response.json()
            self.session_token = data["session_token"]
            self.device_id = data["device_id"]
            self.property_id = data["property_id"]
            self.heartbeat_endpoint = data["heartbeat_endpoint"]
            self.event_endpoint = data["event_endpoint"]
            self.connected = True
            logging.info("Successfully connected to Sentinel Gateway for device %s.", self.device_id)
            return True
        except requests.exceptions.RequestException as exc:
            logging.error("Failed to bootstrap connection: %s", exc)
            self.connected = False
            return False

    def _ensure_connected(self) -> bool:
        if self.connected and self.session_token and self.device_id is not None:
            return True
        if self.bootstrap_token:
            return self.connect()
        return False

    def _post_with_reconnect(self, url: str, payload: dict[str, Any]) -> bool:
        if not self._ensure_connected():
            return False
        try:
            response = self.session.post(url, json=payload, headers=self._headers(), timeout=15)
            if response.status_code == 401:
                logging.warning("Session token expired or invalid. Reconnecting with provisioning token.")
                self.connected = False
                self.session_token = None
                if not self.bootstrap_token or not self.connect():
                    return False
                response = self.session.post(url, json=payload, headers=self._headers(), timeout=15)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as exc:
            logging.error("Gateway request failed: %s", exc)
            return False

    def send_event(
        self,
        alert_type: str,
        vendor_event_id: str,
        occurred_at: Any,
        metadata_json: dict[str, Any],
        media_file_path: str | None = None,
    ) -> bool:
        """Transmit a normalized edge event to the backend gateway."""
        if not self._ensure_connected() or self.device_id is None:
            return False
        normalized_type, normalized_metadata = normalize_edge_event(alert_type, metadata_json)
        media_refs: list[str] = []
        if media_file_path and os.path.exists(media_file_path):
            media_refs.append(media_file_path)
        payload = {
            "alert_type": normalized_type,
            "vendor_event_id": vendor_event_id,
            "occurred_at": serialize_occurred_at(occurred_at),
            "metadata_json": normalized_metadata,
            "media_refs": media_refs,
        }
        url = self._resolve_url(
            self.event_endpoint,
            f"/api/v1/gateway/raspberry-pi/devices/{self.device_id}/events",
        )
        self._work_queue.put((url, payload))
        return True

    def send_heartbeat(
        self,
        cpu_temp: float,
        latency_ms: int,
        *,
        network_status: str = "online",
        power_status: str = "direct_power",
        battery_level: int | None = 100,
        ip_address: str | None = None,
    ) -> bool:
        if not self._ensure_connected() or self.device_id is None:
            return False
        payload = {
            "network_status": network_status,
            "power_status": power_status,
            "battery_level": battery_level,
            "ip_address": ip_address,
            "metadata_json": {
                "cpu_temp_c": cpu_temp,
                "network_latency_ms": latency_ms,
                "client_version": self.client_version,
            },
        }
        url = self._resolve_url(
            self.heartbeat_endpoint,
            f"/api/v1/gateway/raspberry-pi/devices/{self.device_id}/heartbeat",
        )
        self._work_queue.put((url, payload))
        return True
