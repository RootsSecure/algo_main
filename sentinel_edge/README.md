# Sentinel Edge AI Node

Sentinel Edge is the on-site hardware agent for NRI Plot Sentinel. It is designed for Raspberry Pi 4 class hardware, but the same client flow can also run on a normal Linux PC with a supported camera.

The edge node watches a local camera feed, filters for motion, runs object detection only when needed, applies local rules, and sends normalized events plus health heartbeats to the backend gateway.

## Main Responsibilities

- Capture dual camera streams for low-cost inference and high-resolution proof
- Apply a motion gate before heavier model execution
- Run NCNN-backed YOLO inference when motion is present
- Use local logic to detect cases such as illegal construction or soil theft
- Connect to the backend with the secure gateway token flow
- Upload heartbeats and normalized event payloads

## Hardware Profile

Recommended:
- Raspberry Pi 4 Model B, 4GB or 8GB RAM
- Raspberry Pi Camera Module or USB webcam
- Reliable power supply
- High-endurance microSD card

Fallback development mode:
- Linux PC with a USB webcam
- OpenCV fallback camera capture if Picamera2 is unavailable

## Beginner Setup

### 1. Install system packages on Raspberry Pi

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-venv python3-opencv libatlas-base-dev python3-libcamera
```

### 2. Create the edge virtual environment

```bash
cd sentinel_edge
python3 -m venv venv --system-site-packages
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
export SENTINEL_BASE_URL="http://your-server-ip-or-domain:8000"
export SENTINEL_BOOTSTRAP_TOKEN="your-device-provisioning-token"
export SENTINEL_HARDWARE_ID="edge-jaipur-plot-01"
export SENTINEL_CAMERA_MODEL="Pi Camera Module 3"
export SENTINEL_CLIENT_VERSION="sentinel-edge-0.2.0"
```

`SENTINEL_BOOTSTRAP_TOKEN` should come from the backend gateway provision endpoint for a registered device.

### 4. Run the edge node

You can run it directly from inside `sentinel_edge`:

```bash
python core/main.py
```

The startup path now adjusts `sys.path` so that this command works when launched from the edge directory itself.

## Windows Training With DirectML

The repository now includes a Windows-first training path under `sentinel_edge/training/` that prepares your mixed local datasets into a single YOLO dataset and can launch Ultralytics training with a DirectML device.

Typical flow:

```bash
powershell -ExecutionPolicy Bypass -File training/setup_directml_env.ps1
.\directml_venv\Scripts\Activate.ps1
python -m sentinel_edge.training.prepare_composite_dataset --force
python -m sentinel_edge.training.train_detector --prepare --device directml --epochs 50 --imgsz 640
```

Notes:

- DirectML training uses `torch-directml`, so it should be run from a Python 3.10-3.12 environment on Windows.
- The training script disables AMP automatically when `--device directml` is used, because DirectML does not provide the same autocast path as CUDA.
- Prepared labels are written in the class order `person`, `jcb`, `tractor`, `truck`.
- When you deploy exported NCNN weights on the edge node, set `SENTINEL_CLASS_NAMES_FILE` to the generated `classes.txt` so the alert logic can map detections by name instead of brittle numeric IDs.

## Backend Contract

The edge node uses the backend gateway flow:

1. Connect with `POST /api/v1/gateway/raspberry-pi/connect`
2. Receive a short-lived session token plus device-scoped endpoints
3. Send heartbeat payloads to the returned heartbeat endpoint
4. Send normalized events to the returned event endpoint

Edge-side custom detections like `ILLEGAL_CONSTRUCTION` are normalized into backend-supported event types with metadata carrying the higher-level meaning and recommended severity.

## Production Deployment with systemd

Example service file:

```ini
[Unit]
Description=NRI Plot Sentinel Edge AI
After=network.target

[Service]
Type=notify
User=pi
WorkingDirectory=/home/pi/sentinel_edge
Environment="SENTINEL_BASE_URL=http://127.0.0.1:8000"
Environment="SENTINEL_BOOTSTRAP_TOKEN=your-token-goes-here"
Environment="SENTINEL_HARDWARE_ID=edge-jaipur-plot-01"
Environment="SENTINEL_CAMERA_MODEL=Pi Camera Module 3"
ExecStart=/home/pi/sentinel_edge/venv/bin/python core/main.py
Restart=always
WatchdogSec=60s

[Install]
WantedBy=multi-user.target
```

Enable it with:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sentinel-edge.service
sudo systemctl start sentinel-edge.service
journalctl -u sentinel-edge.service -f
```

## Folder Guide

- `core/main.py`: main orchestration loop
- `vision/camera.py`: hardware camera and OpenCV fallback capture
- `vision/inference.py`: motion gate and NCNN inference wrapper
- `logic/rules.py`: local detection heuristics and alert generation
- `network/api_client.py`: Handles secure handshakes with the backend API, securely trading provision tokens for session locks.
- `system/monitor.py`: Directly queries Pi hardware metrics like thermal footprint and calculates network latency.

---

## 📡 Gateway API Specifications

The Edge Node transmits a structured payload to the `/events` endpoint of the NRI Plot Sentinel backend whenever the Logic Engine generates a trigger.

### `/events` Payload Schema

```json
{
  "alert_type": "manual_report", 
  "vendor_event_id": "evt_ILLEGAL_CONSTRUCTION_1684534800000",
  "occurred_at": "2026-04-12T16:00:00+00:00",
  "metadata_json": {
    "edge_event_type": "ILLEGAL_CONSTRUCTION",
    "recommended_severity": "critical",
    "reason": "JCB actively detected",
    "logic_level": "CRITICAL",
    "motion_ratio": 0.08
  },
  "media_refs": ["/tmp/proof_1684534800.jpg"] 
}
```
*Note: If `media_refs` are populated with valid local paths during execution, `api_client.py` will automatically parse and upload the raw binary blob via a `multipart/form-data` stream alongside this JSON definition.*
