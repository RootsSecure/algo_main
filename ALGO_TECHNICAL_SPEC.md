# RootsSecure: ALGO_MAIN Technical Specification

This document provides a comprehensive technical breakdown of the `algo_main` repository, which serves as the core intelligence hub for the **RootsSecure (NRI Plot Sentinel)** Edge Node.

---

## 1. System Architecture: Hybrid Python/C++
The repository implements a high-performance, asynchronous vision pipeline that combines the flexibility of Python with the raw speed of C++.

-   **Python Layer**: Orchestrates high-level logic, network communications (MQTT/API), system monitoring (SDNotify/Systemd), and scheduled tasks.
-   **C++ Native Core (`sentinel_vision`)**: Handles high-frequency tasks: frame capture via V4L2, background subtraction (MOG2), and INT8 Neural Inference (NCNN).

---

## 2. The Native Vision Core (`sentinel_vision.so`)
Built using **Pybind11**, the native core resides in `sentinel_edge/vision_cpp/` and is the performance engine of the sentinel.

### A. Asynchronous Frame Capture
-   **Method**: `cv::VideoCapture` with `cv::CAP_V4L2` backend.
-   **Threading**: A dedicated `capture_loop` thread runs independently of the main Python loop to ensure zero frame drops at 1080p.
-   **Locking**: Uses `std::mutex` and `std::atomic<bool>` for thread-safe frame access.

### B. MOG2 Motion Gating
-   **Logic**: Before running neural inference, the C++ core applies a **Mixture of Gaussians (MOG2)** background subtractor.
-   **Threshold**: Returns `has_motion = true` only if the non-zero pixel ratio exceeds the `threshold_ratio` (default: 5%). This saves significant power on ARM hardware.

### C. NCNN Inference Engine
-   **Model Architecture**: YOLO (optimized for edge).
-   **Acceleration**: Configured to use **Vulkan Compute** and utilizes **4 threads** on the Raspberry Pi 4's ARMv8 cores.
-   **Input**: Normalized 320x320 RGB mat.
-   **Output**: Bounding boxes, class IDs, and confidence scores mapped directly to Python `dict` objects.

---

## 3. Heuristic Logic Engine (`rules.py`)
The "Intelligence" of the sentinel is defined by heuristic rules that analyze the temporal and spatial consistency of detections.

### I. The 5-Frame Construction Rule
-   Detects `jcb` or `excavator` classes.
-   **Requirement**: High-confidence detection for **5 consecutive frames**.
-   **Why**: Prevents false alerts from fleeting reflections or shadows that might momentarily resemble heavy machinery.

### II. Soil Theft Logic
-   **Multi-Object Association**: Triggers an alert if both a `tractor` and a `person` (or worker/shovel) are present in the same scene.
-   **Action**: Indicates unauthorized digging or loading activity on the vacant plot.

### III. Stationary Escalation (Centroid Tracking)
-   **Drift Check**: Calculates centroid migration between frames.
-   **Tolerance**: Allows for **10% variance** in bounding box dimensions and position to account for wind-induced camera shake.
-   **Escalation**: If a `tractor` remains stationary within this variance anchor for **> 5 minutes**, the alert level is escalated to `CRITICAL`.

---

## 4. Network & Communications (`api_client.py`)
The node communicates with the RootsSecure Gateway using a resilient, non-blocking client.

-   **Transport**: REST API (for events and heartbeats) and MQTT (for live telemetry).
-   **Security**: Uses a **Bootstrap Token** for initial provisioning and hardware-linked IDs.
-   **Event Structure**:
    -   **JSON Metadata**: Includes motion ratio, logic levels, and detection duration.
    -   **Visual Proof**: Attaches a high-resolution 1080p JPEG captured natively at the exact moment of the trigger.

---

## 5. System Integration & Reliability
-   **Systemd Watchdog**: Integrates with Linux `sdnotify` to stroke the systemd watchdog. If the main Python loop hangs, systemd will auto-restart the service.
-   **Thermal Monitoring**: Periodically checks SoC temperature to prevent thermal throttling during high-inference summer months in rural India.
-   **Simulation Mode**: Detects dev environments (Windows/macOS) to bypass C++ requirements and inject mock telemetry for rapid dashboard development.

---

## 6. Build & Deployment
-   **Compilation**: Use `cmake` to build the `sentinel_vision` shared library.
-   **Requirements**: OpenCV 4.x, NCNN, Pybind11, and a Vulkan-capable driver.
-   **Target Hardware**: Raspberry Pi 4 / 5 (ARMv8).

---
*Technical Specification maintained by Antigravity AI - RootsSecure Logic Team*
