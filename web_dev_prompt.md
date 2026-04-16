# NRI Plot Sentinel Dashboard - Web Development Prompt

**Dear Web Development Team,**

Please build a premium, highly responsive React web application named **NRI Plot Sentinel Dashboard**. 
This application serves as the primary owner-facing interface for a backend-first MVP designed to remotely secure vacant land plots owned by Non-Resident Indians (NRIs). The system detects unauthorized entry, encroachment, suspicious construction, and device tampering.

Here is the detailed outline of the algorithms, features, and design aesthetics required for the frontend.

## 1. Design Aesthetics & UI/UX (CRITICAL)
The application must feel highly professional, trustworthy, and premium, as the target audience is NRI landowners managing valuable real estate assets from abroad.

*   **Theme:** Deep Dark Mode.
*   **Aesthetic Style:** Glassmorphism (subtle blurs, translucent layers, frosted glass effects).
*   **Colors:** Avoid generic plain colors. Use a highly curated, harmonious color palette with vibrant accents to indicate status (e.g., green for healthy heartbeats, glowing amber for warnings, deep crimson for critical incidents).
*   **Typography:** Modern, clean, and highly legible fonts suitable for dashboards (e.g., Inter, Roboto, or Outfit). No browser defaults.
*   **Interactivity:** Smooth micro-animations for interactions (hover effects, status changes, loading states, modal opening/closing). The interface should feel alive and highly responsive.
*   **Layout:** Dashboard-centric layout with a persistent sidebar or top navigation, a prominent metrics area, and expandable detail panels. Fully responsive across desktop, tablet, and mobile browsers.

## 2. Core Features to Implement

### A. Authentication & Access Workflow
*   **Login/Registration:** Secure JWT-based login (handle access and refresh tokens).
*   **Delegation System:** Interfaces to invite family members or caretakers as delegates and to accept role-aware invites.

### B. Property & Zone Management
*   **Plot Onboarding Wizard:** Multi-step form to add new properties (location coordinates, site type, risk profile, and escalation plans).
*   **Zone Definition:** UI to visually or textually define monitoring sub-zones (e.g., gates, edges, blind spots, sensitive areas).

### C. Hardware Telemetry Dashboard
*   **Device Roster:** List of registered camera nodes (Raspberry Pi/Edge devices) linked to a property.
*   **Health Status:** Visual indicators covering install location, power supply status, network latency/strength, thermal footprint, and battery state.
*   **Heartbeat Tracking:** Real-time visual pipeline showing device online/offline status, prominently surfacing stale or disconnected devices.
*   **Device Provisioning Flow:** A UI wizard for "Local Provisioning". It involves fetching a `BOOTSTRAP_TOKEN` from the backend to display to the owner/operator so they can configure new Raspberry Pi devices on-site.

### D. Event Timeline & Security Evidence
*   **Alert Feed:** A chronological timeline of normalized alerts ingested from edge devices.
*   **Incident Triage:** Ability to click an alert to view an expanded Incident Panel.
*   **Evidence Viewer:** Display attached visual evidence (images/videos from the camera feeds).
*   **Verification:** Buttons to classify severity, mark an incident as verified, or dismiss false alarms.

### E. Response Workflow
*   **Partner Directory:** List of response partners (local security, police proxies).
*   **Dispatch Action:** Trigger an action to dispatch a partner to a verified incident.
*   **Outcome Tracking:** UI to track the partner's arrival, reading closure notes, and resolving incidents with structured outcomes.
*   **Export:** Option to export a summary of the incident (PDF/CSV wrapper).

## 3. Algorithmic Context (For Your Awareness)
While the frontend doesn't run these algorithms, you must design the UI to gracefully represent their outputs from the API:
*   **Edge AI Pipeline:** The physical site uses Sentinel Edge Nodes (Raspberry Pi 4) which capture dual camera feeds.
*   **Motion Gate & YOLO:** The node applies a motion-gate algorithm. If motion is detected, it runs an NCNN-backed YOLO INT8 inference engine for object detection.
*   **Local Logic Heuristics:** The Edge device runs local rules (e.g., detecting a JCB machine means "ILLEGAL_CONSTRUCTION", or specific movements indicate "Soil Theft").
*   **Data Contract:** The frontend will consume events like `edge_event_type: "ILLEGAL_CONSTRUCTION"` with metadata such as `motion_ratio: 0.08` and `logic_level: "CRITICAL"`. Your UI must parse this JSON payload and display it as intuitive, owner-friendly visual alerts rather than raw JSON data.

Please structure the React project cleanly, using best practices for state management and routing. Let's make this dashboard look spectacular!
