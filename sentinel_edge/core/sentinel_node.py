import cv2
import time
import json
import ssl
import threading
import logging
import os
import psutil
import socket
import tempfile
import paho.mqtt.client as mqtt
from picamera2 import Picamera2
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# ---------------------------------------------------------------------------
# Configuration Constants (Cloud-Native v2.0)
# ---------------------------------------------------------------------------
NODE_ID = os.environ.get("SENTINEL_NODE_ID", "NODE_001")
FIRMWARE_VERSION = "2.0.0"

# Cloud MQTT Broker (HiveMQ / AWS IoT Core / EMQX)
MQTT_CLOUD_BROKER = os.environ.get("MQTT_CLOUD_BROKER", "broker.hivemq.cloud")
MQTT_CLOUD_PORT = int(os.environ.get("MQTT_CLOUD_PORT", "8883"))
MQTT_CLOUD_USER = os.environ.get("MQTT_CLOUD_USER", "")
MQTT_CLOUD_PASS = os.environ.get("MQTT_CLOUD_PASS", "")

# Cloud Storage (AWS S3 / Firebase / GCS)
CLOUD_BUCKET_NAME = os.environ.get("SENTINEL_CLOUD_BUCKET", "rootssecure-evidence")

# Local buffer for frames pending upload
LOCAL_BUFFER_DIR = "/tmp/sentinel_buffer/"
STORAGE_THRESHOLD_PERCENT = 80.0
HEARTBEAT_INTERVAL = 60

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_local_ip():
    """Fetch the current active local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def upload_to_cloud(local_path, cloud_key):
    """
    Upload a local file to a cloud storage bucket and return a public/pre-signed URL.
    
    This is a placeholder implementation. Replace the body of this function
    with actual SDK calls for your chosen cloud provider:
    
    - AWS S3:       boto3.client('s3').upload_file(...) + generate_presigned_url(...)
    - Firebase:     firebase_admin.storage.bucket().blob(...).upload_from_filename(...)
    - Google Cloud: google.cloud.storage.Client().bucket(...).blob(...).upload_from_filename(...)
    """
    # --- PLACEHOLDER: Simulate a cloud upload ---
    logging.info(f"[CloudUpload] Uploading {local_path} -> bucket:{CLOUD_BUCKET_NAME}/{cloud_key}")

    # In production, replace the line below with actual upload logic.
    # The function should return the publicly accessible URL of the uploaded file.
    simulated_url = f"https://{CLOUD_BUCKET_NAME}.s3.amazonaws.com/{cloud_key}"

    # After a real upload succeeds, delete the local temp file:
    # try:
    #     os.remove(local_path)
    # except OSError:
    #     pass

    return simulated_url


# ---------------------------------------------------------------------------
# Phase 1: Motion Gating (MOG2)
# ---------------------------------------------------------------------------

class MotionGate:
    """Blocks expensive inference until pixel-change ratio exceeds threshold."""
    def __init__(self, threshold=0.05):
        self.mog2 = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )
        self.threshold = threshold

    def has_motion(self, frame):
        fg_mask = self.mog2.apply(frame)
        motion_ratio = cv2.countNonZero(fg_mask) / (frame.shape[0] * frame.shape[1])
        return motion_ratio >= self.threshold, motion_ratio


# ---------------------------------------------------------------------------
# Phase 3: Heuristic Logic Engine
# ---------------------------------------------------------------------------

class LogicEngine:
    """Converts raw detections into high-level security alerts."""
    def __init__(self):
        self.jcb_frames = 0
        self.tractor_start_pos = None
        self.tractor_start_time = None
        self.variance_threshold = 0.10

    def evaluate(self, detections):
        alerts = []
        labels = {d['class'] for d in detections}

        # Rule 1: JCB 5-Frame Persistence
        if 'jcb' in labels:
            self.jcb_frames += 1
            if self.jcb_frames >= 5:
                alerts.append({
                    "type": "ILLEGAL_CONSTRUCTION",
                    "level": "CRITICAL",
                    "reason": "JCB persistence detected (5-frame rule triggered)"
                })
                self.jcb_frames = -10  # Cooldown
        else:
            self.jcb_frames = max(0, self.jcb_frames - 1)

        # Rule 2: Tractor + Person Contextual Trigger
        if 'tractor' in labels and ('person' in labels or 'worker' in labels):
            alerts.append({
                "type": "SOIL_THEFT_ACTIVE",
                "level": "HIGH",
                "reason": "Tractor and personnel associated"
            })

        # Rule 3: Stationary Tractor Centroid Drift Analysis
        tractor_det = next((d for d in detections if d['class'] == 'tractor'), None)
        if tractor_det:
            curr_pos = tractor_det['bbox']
            if self.tractor_start_pos is None:
                self.tractor_start_pos = curr_pos
                self.tractor_start_time = time.time()
            else:
                dx = abs(curr_pos[0] - self.tractor_start_pos[0]) / self.tractor_start_pos[2]
                dy = abs(curr_pos[1] - self.tractor_start_pos[1]) / self.tractor_start_pos[3]
                if dx > self.variance_threshold or dy > self.variance_threshold:
                    self.tractor_start_pos = curr_pos
                    self.tractor_start_time = time.time()
                elif time.time() - self.tractor_start_time > 300:  # 5 minutes
                    alerts.append({
                        "type": "SOIL_THEFT_ESCALATION",
                        "level": "CRITICAL",
                        "reason": "Stationary tractor > 5 mins"
                    })
                    self.tractor_start_time = time.time()
        return alerts


# ---------------------------------------------------------------------------
# Main Node: Cloud-Native Sentinel
# ---------------------------------------------------------------------------

# Motion-based anomaly detection thresholds
MOTION_SUSTAINED_FRAMES = 5       # Consecutive frames with motion to trigger alert
MOTION_HIGH_RATIO = 0.15          # High motion ratio = significant activity
ALERT_COOLDOWN_SECONDS = 30       # Minimum seconds between alerts
BURST_SNAP_COUNT = 3              # Number of snapshots per anomaly event
BURST_SNAP_INTERVAL = 1.0         # Seconds between burst snapshots


class SentinelNode:
    def __init__(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s'
        )

        self.motion_gate = MotionGate()
        self.logic = LogicEngine()
        self.cloud_connected = False

        # Motion tracking state
        self.consecutive_motion_frames = 0
        self.last_alert_time = 0

        # --- Cloud MQTT Setup (TLS on port 8883) ---
        self.mqtt = mqtt.Client(
            client_id=NODE_ID,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.mqtt.username_pw_set(MQTT_CLOUD_USER, MQTT_CLOUD_PASS)
        self.mqtt.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
        self.mqtt.tls_insecure_set(False)

        self.mqtt.on_connect = self._on_connect
        self.mqtt.on_disconnect = self._on_disconnect

        try:
            self.mqtt.connect(MQTT_CLOUD_BROKER, MQTT_CLOUD_PORT, 60)
            self.mqtt.loop_start()
        except Exception as e:
            logging.error(f"Cloud MQTT connection failed: {e}. Will retry in background.")
            self.mqtt.loop_start()  # Paho will auto-reconnect

        # Local buffer directory for frames pending cloud upload
        Path(LOCAL_BUFFER_DIR).mkdir(parents=True, exist_ok=True)

        # Start background threads
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()
        threading.Thread(target=self._retry_upload_loop, daemon=True).start()

    # --- MQTT Callbacks ---

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            self.cloud_connected = True
            logging.info(f"Connected to Cloud MQTT Broker: {MQTT_CLOUD_BROKER}:{MQTT_CLOUD_PORT}")
        else:
            self.cloud_connected = False
            logging.error(f"Cloud MQTT connection refused (rc={rc})")

    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        self.cloud_connected = False
        logging.warning(f"Disconnected from Cloud MQTT (rc={rc}). Auto-reconnecting...")

    # --- Heartbeat (Non-blocking background thread) ---

    def _heartbeat_loop(self):
        while True:
            try:
                payload = {
                    "node_id": NODE_ID,
                    "cpu_temp_c": self._get_cpu_temp(),
                    "ram_usage_percent": psutil.virtual_memory().percent,
                    "battery_percent": 100,
                    "network_latency_ms": 0,
                    "power_status": "AC_CONNECTED",
                    "storage_usage_percent": psutil.disk_usage('/').percent,
                    "uplink_status": "CLOUD_CONNECTED" if self.cloud_connected else "CLOUD_DISCONNECTED",
                    "firmware_version": FIRMWARE_VERSION
                }
                self.mqtt.publish(
                    f"sentinel/{NODE_ID}/heartbeat",
                    json.dumps(payload),
                    qos=0
                )
                logging.info(f"Heartbeat sent | CPU: {payload['cpu_temp_c']}°C | Uplink: {payload['uplink_status']}")
            except Exception as e:
                logging.error(f"Heartbeat error: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

    # --- Retry Loop: Upload buffered frames that failed earlier ---

    def _retry_upload_loop(self):
        """Retries uploading any frames stuck in the local buffer."""
        while True:
            time.sleep(60)
            try:
                buffer_path = Path(LOCAL_BUFFER_DIR)
                pending = list(buffer_path.glob("*.jpg"))
                if pending:
                    logging.info(f"[RetryUpload] {len(pending)} buffered frame(s) found. Retrying...")
                for f in pending:
                    cloud_key = f"evidence/{NODE_ID}/{datetime.utcnow().strftime('%Y-%m-%d')}/{f.stem}.jpg"
                    try:
                        upload_to_cloud(str(f), cloud_key)
                        f.unlink()  # Remove local copy after successful upload
                        logging.info(f"[RetryUpload] Successfully uploaded: {f.name}")
                    except Exception as e:
                        logging.warning(f"[RetryUpload] Failed for {f.name}: {e}")
            except Exception as e:
                logging.error(f"[RetryUpload] Loop error: {e}")

    # --- System Helpers ---

    def _get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read()) / 1000.0
        except Exception:
            return 0.0

    # --- Cloud Media Upload ---

    def _upload_evidence(self, frame, event_id):
        """
        Save frame locally, upload to cloud, return cloud URL.
        Falls back to local buffer if upload fails.
        """
        date_str = datetime.utcnow().strftime('%Y-%m-%d')
        filename = f"{event_id}.jpg"
        local_path = os.path.join(LOCAL_BUFFER_DIR, filename)
        cloud_key = f"evidence/{NODE_ID}/{date_str}/{filename}"

        # Save frame to local buffer first
        cv2.imwrite(local_path, frame)

        try:
            cloud_url = upload_to_cloud(local_path, cloud_key)
            # On successful upload, remove local copy
            try:
                os.remove(local_path)
            except OSError:
                pass
            return cloud_url
        except Exception as e:
            logging.warning(f"Cloud upload failed ({e}). Frame buffered locally for retry.")
            return None

    # --- 3-Frame Burst Capture ---

    def _capture_burst(self, cam):
        """
        Captures 3 high-resolution snapshots at 1-second intervals.
        Returns a list of cloud URLs for the uploaded evidence.
        """
        event_id = str(uuid4())
        media_urls = []

        logging.info(f"[BURST] Capturing {BURST_SNAP_COUNT} evidence snapshots...")

        for i in range(BURST_SNAP_COUNT):
            snap_id = f"{event_id}_snap{i+1}"
            proof_frame = cam.capture_array("main")
            proof_bgr = cv2.cvtColor(proof_frame, cv2.COLOR_RGB2BGR)

            # Add timestamp overlay to the image
            timestamp_text = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            cv2.putText(
                proof_bgr, f"SENTINEL | {timestamp_text} | Snap {i+1}/{BURST_SNAP_COUNT}",
                (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2
            )

            cloud_url = self._upload_evidence(proof_bgr, snap_id)
            if cloud_url:
                media_urls.append(cloud_url)

            logging.info(f"[BURST] Snap {i+1}/{BURST_SNAP_COUNT} captured: {snap_id}")

            # Wait between snaps (except after the last one)
            if i < BURST_SNAP_COUNT - 1:
                time.sleep(BURST_SNAP_INTERVAL)

        return event_id, media_urls

    # --- Main Vision Loop ---

    def run(self):
        logging.info(f"Sentinel Node {NODE_ID} (Cloud-Native v{FIRMWARE_VERSION}) Operational.")

        # Initialize Picamera2 (Raspberry Pi OS Bookworm)
        cam = Picamera2()
        config = cam.create_video_configuration(
            main={"size": (1920, 1080), "format": "RGB888"},
            lores={"size": (640, 480), "format": "YUV420"},
            buffer_count=4
        )
        cam.configure(config)
        cam.start()
        time.sleep(2)  # Camera warmup
        logging.info("Picamera2 initialized and streaming.")

        try:
            while True:
                # Capture frame from the low-res YUV stream for motion detection
                frame_yuv = cam.capture_array("lores")
                frame_bgr = cv2.cvtColor(frame_yuv, cv2.COLOR_YUV420p2BGR)

                # Phase 1: Motion Gate
                is_motion, ratio = self.motion_gate.has_motion(frame_bgr)

                if is_motion:
                    self.consecutive_motion_frames += 1
                else:
                    self.consecutive_motion_frames = max(0, self.consecutive_motion_frames - 1)

                # --- Anomaly Trigger ---
                # Fire alert if sustained motion detected for 5+ frames
                # OR if a single frame has very high motion (> 15%)
                now = time.time()
                should_alert = (
                    (self.consecutive_motion_frames >= MOTION_SUSTAINED_FRAMES or ratio >= MOTION_HIGH_RATIO)
                    and (now - self.last_alert_time) > ALERT_COOLDOWN_SECONDS
                )

                if should_alert:
                    self.last_alert_time = now
                    self.consecutive_motion_frames = 0

                    # Determine severity based on motion intensity
                    if ratio >= 0.30:
                        severity = "CRITICAL"
                        event_type = "MAJOR_INTRUSION"
                        reason = f"Massive motion detected (ratio: {ratio:.2%})"
                    elif ratio >= MOTION_HIGH_RATIO:
                        severity = "HIGH"
                        event_type = "PERSON_DETECTED"
                        reason = f"Significant motion detected (ratio: {ratio:.2%})"
                    else:
                        severity = "MEDIUM"
                        event_type = "MOTION_ANOMALY"
                        reason = f"Sustained motion detected for {MOTION_SUSTAINED_FRAMES}+ frames (ratio: {ratio:.2%})"

                    logging.warning(f"ANOMALY DETECTED: {event_type} | Ratio: {ratio:.4f}")

                    # Capture 3-frame burst evidence
                    event_id, media_urls = self._capture_burst(cam)

                    # Publish alert with all 3 snapshot URLs
                    alert_payload = {
                        "vendor_event_id": event_id,
                        "alert_type": "Auto",
                        "occurred_at": datetime.utcnow().isoformat() + "Z",
                        "node_id": NODE_ID,
                        "metadata_json": {
                            "edge_event_type": event_type,
                            "recommended_severity": severity,
                            "logic_level": severity,
                            "reason": reason,
                            "motion_ratio": round(ratio, 4),
                            "inference_model": "motion-gate-v2",
                            "burst_count": len(media_urls),
                            "confidence": round(min(ratio * 5, 1.0), 2)
                        },
                        "media_refs": media_urls
                    }
                    self.mqtt.publish(
                        f"sentinel/{NODE_ID}/alerts",
                        json.dumps(alert_payload),
                        qos=1
                    )
                    logging.warning(
                        f"ALERT DISPATCHED: {event_type} | "
                        f"Severity: {severity} | "
                        f"Evidence: {len(media_urls)} snapshots"
                    )

                time.sleep(0.03)  # ~30 FPS yield

        except KeyboardInterrupt:
            logging.info("Shutting down gracefully...")
        finally:
            cam.stop()
            cam.close()
            logging.info("Camera released. Sentinel stopped.")


if __name__ == "__main__":
    SentinelNode().run()
