# RootsSecure Algorithm Deep Dive: The Digital Panopticon Engine

This document provides a detailed technical breakdown of the multi-stage Edge AI pipeline used in the **RootsSecure (NRI Plot Sentinel)** project.

---

## 1. Pipeline Overview
The algorithm operates as a tiered "filter" system to maximize detection accuracy while minimizing computational overhead on hardware like the Raspberry Pi 4.

1.  **Phase 1: Motion Gating (MOG2)** - Efficient pixel-level change detection.
2.  **Phase 2: Neural Inference (NCNN YOLO)** - High-fidelity object classification.
3.  **Phase 3: Logic Engine (Heuristics)** - Contextual threat evaluation and temporal analysis.

---

## 2. Phase 1: Motion Gating
To prevent the expensive Neural Network from running on static frames (e.g., empty land at night), the system uses a **MotionGate** module.

-   **Algorithm**: `cv2.createBackgroundSubtractorMOG2` (Mixture of Gaussians).
-   **Gating Logic**: Calculates the `motion_ratio` (changed pixels / total pixels).
-   **Threshold**: By default, if `motion_ratio < 0.05` (5%), the pipeline skips the inference stage to save power and thermal headroom.

---

## 3. Phase 2: Neural Inference (NCNN YOLO)
Once motion is confirmed, the frame is passed to the **NCNNYoloInferencer**.

-   **Backend**: **NCNN** (high-performance neural network inference framework optimized for mobile/edge platforms).
-   **Acceleration**: Utilizes **Vulkan GPU compute** where available.
-   **Model Details**: 
    -   Architecture: YOLO (optimized for edge).
    -   Input Resolution: 320x320 pixels (standardized for rapid inference).
    -   Quantization: INT8 (drastically reduces memory footprint and latency).
-   **Confidence Threshold**: Objects are ignored if detection confidence is `< 0.3`.

---

## 4. Phase 3: The Sentinel Logic Engine
The core intelligence resides in the `SentinelLogicEngine`. It converts raw bounding boxes into high-level security events.

### A. Illegal Construction Detection (`ILLEGAL_CONSTRUCTION`)
-   **Target**: JCBs, Excavators, or heavy machinery.
-   **The 5-Frame Rule**: To avoid false positives from brief visual noise, the system requires a `jcb` class to be detected in **5 consecutive frames** before triggering an alert.
-   **Cooldown**: Once triggered, it enters a -10 frame cooldown to prevent alert flooding.

### B. Soil Theft Detection (`SOIL_THEFT_ACTIVE`)
-   **Contextual Trigger**: Activated if a `tractor` and a `person` (or `worker`/`shovel`) are detected in the same frame.
-   **Significance**: A lone tractor might be passing by, but a tractor + humans on a vacant plot indicates active unauthorized work.

### C. Stationary Escalation (`SOIL_THEFT_ESCALATION`)
-   **Drift Analysis**: Uses the `do_boxes_overlap` function to track the centroid of a detected tractor.
-   **Centroid Variance**: Allows for 10% movement variance to ignore camera vibrations or wind.
-   **Time Threshold**: If a tractor remains stationary for **> 5 minutes**, it escalates to a `CRITICAL` alert, indicating potential long-term encroachment or illegal occupation.

---

## 5. System Health & Telemetry
Beyond security alerts, the algorithm continuously tracks its own operational integrity:
-   **Heartbeat**: Periodic MQTT pulses confirm the node is "Armed" and active.
-   **Network Resilience**: Latency tracking to ensure alerts reach the NRI owner across global networks.
-   **Thermal Monitoring**: Prevents AI throttling by tracking CPU/SoC temperatures during heavy inference loads.

---

## 6. Data Contract (JSON Payload)
The output of the engine is a normalized JSON payload for the mobile/web dashboard:

```json
{
  "id": "evt_ILLEGAL_CONSTRUCTION_1684534800000",
  "type": "ILLEGAL_CONSTRUCTION",
  "level": "CRITICAL",
  "metadata": {
    "reason": "JCB actively detected",
    "motion_ratio": 0.08
  }
}
```

---

> [!IMPORTANT]
> **Edge Optimization Note**: The logic engine is designed to be "Simulation-Aware". On non-Android/Linux systems (like Windows development), it can bypass hardware requirements to generate randomized telemetry for UI testing.
