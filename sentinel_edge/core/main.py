import gc
import logging
import os
from pathlib import Path
import sys
import tempfile
import time

try:
    import sdnotify
except ImportError:
    sdnotify = None

PACKAGE_PARENT = Path(__file__).resolve().parents[2]
if str(PACKAGE_PARENT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_PARENT))

from sentinel_edge.network.api_client import SentinelAPIClient
from sentinel_edge.system.monitor import get_cpu_temp, measure_latency
from sentinel_edge.logic.rules import SentinelLogicEngine

try:
    from sentinel_vision import HybridVisionCore
except ImportError:
    HybridVisionCore = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


def load_class_names(labels_path: str | None) -> list[str]:
    if not labels_path:
        return []

    path = Path(labels_path)
    if not path.exists():
        logging.warning("Class names file %s was not found. Falling back to raw class IDs.", path)
        return []

    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def attach_class_labels(detections, class_names):
    if not class_names:
        return detections

    enriched = []
    for detection in detections:
        updated = dict(detection)
        class_id = updated.get("class")
        if isinstance(class_id, int) and 0 <= class_id < len(class_names):
            updated["label"] = class_names[class_id]
        enriched.append(updated)
    return enriched

def main():
    notifier = None
    if sdnotify:
        notifier = sdnotify.SystemdNotifier()
        notifier.notify("READY=1")
        notifier.notify("STATUS=Initializing NRI Plot Sentinel Edge AI")

    # Initial Configuration
    api_base = os.environ.get("SENTINEL_BASE_URL", "http://localhost:8000")
    bootstrap_token = os.environ.get("SENTINEL_BOOTSTRAP_TOKEN", "mock-bootstrap-token")
    hardware_id = os.environ.get("SENTINEL_HARDWARE_ID")
    camera_model = os.environ.get("SENTINEL_CAMERA_MODEL", "Pi Camera Module 3")
    client_version = os.environ.get("SENTINEL_CLIENT_VERSION", "sentinel-edge-0.2.0")
    model_bin_path = os.environ.get("SENTINEL_MODEL_BIN", "yolo26n.bin")
    model_param_path = os.environ.get("SENTINEL_MODEL_PARAM", "yolo26n.param")
    class_names = load_class_names(os.environ.get("SENTINEL_CLASS_NAMES_FILE"))
    
    # 1. Connect API Gateway
    api = SentinelAPIClient(
        api_base,
        bootstrap_token,
        hardware_id=hardware_id,
        camera_model=camera_model,
        client_version=client_version,
    )
    if not api.connect():
        logging.warning("Initial Gateway connection failed. Proceeding in offline mode.")

    # 2. Initialize Components
    if not HybridVisionCore:
        logging.error("Compiled C++ sentinel_vision.so not found in PYTHONPATH. Run 'make' in build/ directory.")
        sys.exit(1)
        
    camera = HybridVisionCore(model_bin_path, model_param_path)
    if not camera.start_camera(0, 1920, 1080):
        logging.error("Failed to start V4L2 Native Camera hook.")
        sys.exit(1)
        
    logic_engine = SentinelLogicEngine()

    last_heartbeat = time.time()
    HEARTBEAT_INTERVAL = 60 * 60  # Once every hour (adjust for production)
    
    logging.info("Starting main inference loop...")
    if notifier:
        notifier.notify("STATUS=Running")

    try:
        while True:
            # 1. Stroke the systemd watchdog to prove the process hasn't hung
            if notifier:
                notifier.notify("WATCHDOG=1")
            
            # ---------------------------------------------------------
            # VISION PIPELINE ARCHITECTURE (Native C++ Extension)
            # ---------------------------------------------------------
            result = camera.process_frame(threshold_ratio=0.05)
            
            if result.get("has_motion"):
                detections = attach_class_labels(result.get("detections", []), class_names)
                
                # Evaluate state machine rules
                alerts = logic_engine.evaluate(detections)
                
                if alerts:
                    # Capture Visual Proof natively
                    proof_1080p_path = str(Path(tempfile.gettempdir()) / f"proof_{int(time.time())}.jpg")
                    camera.save_visual_proof(proof_1080p_path)
                    
                    # Transmit and/or Buffer Events non-blocking
                    for alert in alerts:
                        api.send_event(
                            alert_type=alert.type,
                            vendor_event_id=alert.id,
                            occurred_at=time.time(),
                            metadata_json={
                                **alert.metadata,
                                "logic_level": alert.level,
                                "motion_ratio": float(result.get("motion_ratio", 0.0)),
                            },
                            media_file_path=proof_1080p_path
                        )
                    
                    # Explicit cleanup to guarantee 0 memory leaks per trigger event
                    gc.collect()
            # ---------------------------------------------------------

            # 2. Scheduled Heartbeat Check
            if time.time() - last_heartbeat > HEARTBEAT_INTERVAL:
                cpu_temp = get_cpu_temp()
                latency = measure_latency(api_base)
                logging.info(f"Uploading Heartbeat - CPU: {cpu_temp}C, Ping: {latency}ms")
                api.send_heartbeat(cpu_temp, latency)
                last_heartbeat = time.time()
                
            time.sleep(0.033) # Yield roughly 30 FPS sleep
            
    except KeyboardInterrupt:
        logging.info("Shutting down cleanly.")
        camera.close()
        if notifier:
            notifier.notify("STOPPING=1")
    except Exception as e:
        logging.error(f"Critical error in main loop: {e}", exc_info=True)
        try:
            camera.close()
        except:
            pass
        sys.exit(1) # Let systemd auto-restart the service

if __name__ == "__main__":
    main()
