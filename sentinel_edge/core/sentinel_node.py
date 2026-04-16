import cv2
import time
import json
import threading
import logging
import os
import psutil
import socket # Added for dynamic IP resolution
import paho.mqtt.client as mqtt
from pathlib import Path
from datetime import datetime
from uuid import uuid4

# --- Configuration Constants ---
NODE_ID = os.environ.get("SENTINEL_NODE_ID", "NODE_001")
MQTT_BROKER = "127.0.0.1" # Updated to Localhost for internal resilience
MQTT_PORT = 1883
MEDIA_DIR = "/var/www/html/media/alerts/"
STORAGE_THRESHOLD_PERCENT = 80.0
HEARTBEAT_INTERVAL = 60

def get_local_ip():
    """Robust helper to fetch the current active local IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Using Google's DNS as a target (doesn't need to be reachable) 
        # to force the OS to pick the active outgoing interface.
        s.connect(('8.8.8.8', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class MotionGate:
    """Phase 1: MOG2 Background Subtraction Gating"""
    def __init__(self, threshold=0.05):
        self.mog2 = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=16, detectShadows=False)
        self.threshold = threshold

    def has_motion(self, frame):
        fg_mask = self.mog2.apply(frame)
        motion_ratio = cv2.countNonZero(fg_mask) / (frame.shape[0] * frame.shape[1])
        return motion_ratio >= self.threshold, motion_ratio

class LogicEngine:
    """Phase 3: Heuristic Threat Evaluation"""
    def __init__(self):
        self.jcb_frames = 0
        self.tractor_start_pos = None
        self.tractor_start_time = None
        self.variance_threshold = 0.10 

    def evaluate(self, detections):
        alerts = []
        labels = {d['class'] for d in detections}
        
        # Rule: JCB 5-Frame Persistence
        if 'jcb' in labels:
            self.jcb_frames += 1
            if self.jcb_frames >= 5:
                alerts.append({"type": "ILLEGAL_CONSTRUCTION", "level": "CRITICAL", "reason": "JCB persistence detected"})
                self.jcb_frames = -10 # Cooldown
        else:
            self.jcb_frames = max(0, self.jcb_frames - 1)

        # Rule: Tractor + Person Contextual Trigger
        if 'tractor' in labels and ('person' in labels or 'worker' in labels):
            alerts.append({"type": "SOIL_THEFT_ACTIVE", "level": "HIGH", "reason": "Tractor and personnel associated"})

        # Rule: Stationary Tractor Analysis
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
                elif time.time() - self.tractor_start_time > 300: # 5 mins
                    alerts.append({"type": "SOIL_THEFT_ESCALATION", "level": "CRITICAL", "reason": "Stationary tractor > 5 mins"})
                    self.tractor_start_time = time.time()
        return alerts

class SentinelNode:
    def __init__(self):
        logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
        self.motion_gate = MotionGate()
        self.logic = LogicEngine()
        
        # MQTT Setup: Binding to Localhost (127.0.0.1)
        self.mqtt = mqtt.Client(client_id=NODE_ID)
        self.mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt.loop_start()
        
        Path(MEDIA_DIR).mkdir(parents=True, exist_ok=True)
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def _heartbeat_loop(self):
        while True:
            try:
                payload = {
                    "cpu_temp_c": self._get_cpu_temp(),
                    "ram_usage_percent": psutil.virtual_memory().percent,
                    "battery_percent": 100,
                    "network_latency_ms": 0,
                    "power_status": "AC_CONNECTED",
                    "storage_usage_percent": psutil.disk_usage('/').percent,
                    "local_ip": get_local_ip() # SURFACING IP IN HEARTBEAT
                }
                self.mqtt.publish(f"sentinel/{NODE_ID}/heartbeat", json.dumps(payload), qos=0)
                self._storage_cleanup()
            except Exception as e:
                logging.error(f"Heartbeat loop error: {e}")
            time.sleep(HEARTBEAT_INTERVAL)

    def _get_cpu_temp(self):
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return int(f.read()) / 1000.0
        except: return 0.0

    def _storage_cleanup(self):
        usage = psutil.disk_usage(MEDIA_DIR).percent
        if usage > STORAGE_THRESHOLD_PERCENT:
            files = sorted(Path(MEDIA_DIR).glob("*.jpg"), key=os.path.getmtime)
            for f in files[:len(files)//4]: f.unlink()

    def run(self):
        logging.info(f"Sentinel Node {NODE_ID} (Station Mode) Operational.")
        cap = cv2.VideoCapture(0)
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            is_motion, ratio = self.motion_gate.has_motion(frame)
            if is_motion:
                # Placeholder for NCNN inference call
                detections = [] 
                threats = self.logic.evaluate(detections)
                
                if threats:
                    # DYNAMIC IP RESOLUTION FOR MEDIA URLS
                    current_ip = get_local_ip()
                    filename = f"event_{int(time.time())}.jpg"
                    media_url = f"http://{current_ip}/media/alerts/{filename}"
                    
                    cv2.imwrite(os.path.join(MEDIA_DIR, filename), frame)
                    
                    for t in threats:
                        self.mqtt.publish(f"sentinel/{NODE_ID}/alerts", json.dumps({
                            "vendor_event_id": str(uuid4()), 
                            "alert_type": "Auto",
                            "occurred_at": datetime.utcnow().isoformat() + "Z",
                            "metadata_json": {**t, "motion_ratio": round(ratio, 4)},
                            "media_refs": [media_url] # Using dynamic IP here
                        }), qos=1)
            
            time.sleep(0.01)

if __name__ == "__main__":
    SentinelNode().run()
