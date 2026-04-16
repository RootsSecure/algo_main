# RootsSecure: Project Documentation & Technical Overview

## 1. Core Concept: The "Digital Panopticon"
RootsSecure is an advanced security and telemetry platform designed for NRI (Non-Resident Indian) plot owners. The system follows the **Digital Panopticon** design philosophy: providing total visibility, persistent surveillance, and algorithmic vigilance over physical assets located thousands of miles away.

The primary objective is to detect and alert against specific threats common in rural/vacant plots, such as **Illegal Construction** (JCB/Excavator presence) and **Soil Theft** (Tractor + Shovel/Worker activity).

---

## 2. Tiered System Architecture
The platform is built on a distributed three-tier pipeline to ensure reliability even on low-bandwidth rural networks.

### I. Edge Layer (Raspberry Pi Node)
*   **Hardware**: Raspberry Pi with Camera Module.
*   **Role**: Local sensing, computer vision, and rule-based triaging.
*   **Optimization**: 
    *   **Dual-Stream Capture**: Concurrent capture of 1080p (for visual proof) and 320x320 (for inference) reduces CPU overhead.
    *   **Local State**: The edge node maintains a short-term memory (5-frame logic) to prevent "alert storms" from transient noise.

### II. Transport Layer (MQTT Telemetry)
*   **Protocol**: Lightweight MQTT (`paho-mqtt`).
*   **Payload**: Structured JSON buffers (averaging < 1KB) containing event IDs, threat levels, and confidence scores.
*   **Resilience**: Designed to function over high-jitter 3G/4G cellular connections common in rural India.

### III. Application Layer (Mobile & Service)
*   **Background Listener**: A Python service (`service.py`) running persistently to capture and store telemetry.
*   **Cross-Platform UI**: 
    *   **Python/Kivy**: A rapid-iteration dashboard for real-time visualization.
    *   **Native Kotlin**: A production-ready Android implementation using Jetpack Compose and modern Material Design.
*   **Internal IPC**: Communication between background services and UI is handled via **OSC (Open Sound Control)** on Port 3000 to bypass Python's Global Interpreter Lock (GIL) limitations.

---

## 3. Vision Pipeline & Heuristic Algorithms

### A. MOG2 Motion Gating
To preserve the Pi's CPU life, the expensive YOLO model is "gated."
*   **Algorithm**: Mixture of Gaussians (MOG2) Background Subtraction.
*   **Trigger**: Inference only starts when the **pixel change ratio exceeds 5%** of the frame.
*   **Benefit**: Eliminates redundant processing when nothing is moving in the plot.

### B. Quantized NCNN YOLO
*   **Model**: YOLO11n (Nano) quantized to **INT8 precision**.
*   **Inference Engine**: Tencent's **NCNN**, optimized for ARM-based edge devices.
*   **Hardware Acceleration**: Uses **Vulkan GPU Compute** if the environment supports it (e.g., Pi 4/5).

### C. Logic Engine (Heuristic Triaging)
The `rules.py` engine transforms raw bounding boxes into high-context security alerts:

1.  **Illegal Construction (JCB 5-Frame Rule)**:
    *   A JCB/Excavator must be detected with high confidence for **5 consecutive frames** before an alert is fired. This prevents false positives from fleeting reflections.
2.  **Soil Theft Association**:
    *   Triggered when a **Tractor** and a **Person/Worker/Shovel** are detected in the same scene, implying loading/unloading activity.
3.  **Stationary Escalation (Stationary Tracker)**:
    *   **Anchor Check**: Centroid movement must be within **10% variance** to be considered stationary.
    *   **Timer**: If a Tractor remains in the "Stationary Anchor" for more than **5 minutes**, the level is escalated from `HIGH` to `CRITICAL`.

---

## 4. Key Optimizations

| Optimization | Method | Impact |
| :--- | :--- | :--- |
| **Edge Compute** | Local INT8 Inference | Reduces data egress costs & latency. |
| **Motion Gating** | MOG2 Filtering | Increases hardware longevity and saves power. |
| **Network** | Binary-mapped JSON | Ensures connectivity on edge networks. |
| **UI Rendering** | Kivy-Kotlin Bridge | Combines Python logic flexibility with Native performance. |
| **Spatial Consistency** | Centroid Variance Box Overlap | Mitigates camera shake and environmental noise. |

---

## 5. Design System: Aesthetic Principles
The UI follows strict rules to manage high-stress security monitoring:
*   **Environment**: Obsidian (#131313) background to reduce eye strain.
*   **Accents**: Teal (#55D8E1) for "Active/Secure" state; Crimson for "Critical Threats".
*   **Typography**: 
    *   **Inter**: For readability in alerts and descriptions.
    *   **Space Grotesk**: For raw numerical data (confidence %, epoch duration), providing a technical, high-authority look.

---

## 6. Development & Build Workflow

### Simulation Mode (Windows)
Developers can run `python main.py` on Windows. The logic detects `platform != 'android'` and automatically injects randomized mock JSON telemetry every 10 seconds to allow UI testing without actual hardware.

### Android Compilation
Handled via `Buildozer` on WSL2 (Ubuntu 22.04).
1.  Navigate to `mobile_app/`.
2.  Run `buildozer android debug`.
3.  Pulls NDK/SDK and packages `paho-mqtt`, `oscpy`, and Python logic into a native APK.

### Native Android (Kotlin)
The `d:\NRI app` directory contains a secondary implementation using:
*   **Kotlin + Jetpack Compose**
*   **Dagger Hilt** for Dependency Injection.
*   **Retrofit/Moshi** for network handling.
*   **WorkManager** for background MQTT persistence.

---
*Created by Antigravity AI - Sentinel Documentation Engine*
