# RootsSecure Cloud-Native Architecture Contract

**Version:** 2.0.0  
**Status:** Active — Supersedes Station Mode (v1.x)  
**Effective:** April 2026

---

## 1. Motivation: Why Cloud-Native?

The Station Mode architecture (Raspberry Pi as a local Wi-Fi Access Point) was sufficient for prototyping but fails the core NRI use case:

| Limitation | Impact |
| :--- | :--- |
| Requires physical proximity to the Pi's Wi-Fi | Owner in London cannot receive alerts from a plot in Lucknow |
| Local Mosquitto broker is unreachable over the internet | No remote monitoring without VPN/port forwarding hacks |
| Media served via local Nginx (`192.168.x.x`) | Images are inaccessible outside the local network |
| Single point of failure | Pi reboot = total communication blackout |

**Cloud-Native resolves all of these.** The Pi becomes a "fire-and-forget" sensor that pushes data upward to a globally reachable cloud layer.

---

## 2. Cloud MQTT Topology

### Previous Architecture (Deprecated)
```
Pi → localhost:1883 (Mosquitto) → Phone on same Wi-Fi
```

### New Architecture (Cloud-Native)
```
Pi → TLS:8883 (HiveMQ Cloud) → Mobile App (anywhere in the world)
                               → Web Dashboard (anywhere in the world)
```

### Broker Configuration

| Parameter | Value |
| :--- | :--- |
| **Provider** | HiveMQ Cloud Serverless (or AWS IoT Core / EMQX Cloud) |
| **Endpoint** | `broker.hivemq.cloud` (or your cluster URL) |
| **Port** | `8883` (TLS encrypted) |
| **Protocol** | MQTT v3.1.1 over TLS 1.2+ |
| **Authentication** | Username/Password (provisioned per node) |
| **Topic Structure** | `sentinel/<node_id>/alerts` (QoS 1) |
|  | `sentinel/<node_id>/heartbeat` (QoS 0) |

### Environment Variables (Edge Node)
```bash
export SENTINEL_NODE_ID="NODE_001"
export MQTT_CLOUD_BROKER="<your-cluster>.s1.eu.hivemq.cloud"
export MQTT_CLOUD_PORT=8883
export MQTT_CLOUD_USER="sentinel_node_001"
export MQTT_CLOUD_PASS="<secure-password>"
```

### Security Notes
- All traffic is encrypted end-to-end via TLS.
- Each edge node receives unique credentials during provisioning.
- The local Mosquitto broker is **no longer required** on the Pi.

---

## 3. Cloud Media Strategy

### Previous Strategy (Deprecated)
```
Frame → /var/www/html/media/alerts/ → Nginx on Pi → http://192.168.4.1/media/...
```
**Problem:** Only accessible on the local network.

### New Strategy (Cloud-Native)
```
Frame → Local /tmp/ buffer → Upload to Cloud Bucket → Pre-signed/Public URL → Embedded in MQTT payload
```

### Recommended Cloud Storage Options

| Provider | Service | SDK |
| :--- | :--- | :--- |
| **AWS** | S3 | `boto3` |
| **Google Cloud** | Cloud Storage | `google-cloud-storage` |
| **Firebase** | Firebase Storage | `firebase-admin` |

### Upload Pipeline

1. **Capture**: On threat detection, save the 1080p frame to a local temporary file (`/tmp/proof_<timestamp>.jpg`).
2. **Upload**: Push the file to the cloud bucket under the path: `evidence/<node_id>/<YYYY-MM-DD>/<event_id>.jpg`.
3. **Generate URL**: Obtain a pre-signed URL (valid for 7 days) or a public URL for the uploaded object.
4. **Embed**: Place the cloud URL into the `media_refs` array of the MQTT alert payload.
5. **Cleanup**: Delete the local temporary file after successful upload to conserve SD card space.

### Failure Handling
- If the upload fails (network outage), the frame is retained locally in `/tmp/sentinel_buffer/`.
- A background retry thread attempts re-upload every 60 seconds.
- Once successfully uploaded, the local copy is purged.

---

## 4. Updated JSON Payload Contract

### A. Security Alerts
**Topic:** `sentinel/<node_id>/alerts` (QoS 1)

```json
{
  "vendor_event_id": "a3f8c1d2-7b4e-4f9a-b123-456789abcdef",
  "alert_type": "Auto",
  "occurred_at": "2026-04-17T05:45:00Z",
  "node_id": "NODE_001",
  "metadata_json": {
    "edge_event_type": "ILLEGAL_CONSTRUCTION",
    "recommended_severity": "CRITICAL",
    "logic_level": "CRITICAL",
    "reason": "JCB persistence detected (5-frame rule triggered)",
    "motion_ratio": 0.12,
    "inference_model": "yolo11n-int8-ncnn",
    "confidence": 0.94
  },
  "media_refs": [
    "https://rootssecure-evidence.s3.amazonaws.com/evidence/NODE_001/2026-04-17/a3f8c1d2.jpg?X-Amz-Expires=604800&X-Amz-Signature=..."
  ]
}
```

### B. Hardware Heartbeat (Every 60s)
**Topic:** `sentinel/<node_id>/heartbeat` (QoS 0)

```json
{
  "node_id": "NODE_001",
  "cpu_temp_c": 42.5,
  "ram_usage_percent": 24.1,
  "battery_percent": 85,
  "network_latency_ms": 45,
  "power_status": "AC_CONNECTED",
  "storage_usage_percent": 15.4,
  "uplink_status": "CLOUD_CONNECTED",
  "firmware_version": "2.0.0"
}
```

### Key Changes from v1.0
| Field | v1.0 (Station Mode) | v2.0 (Cloud-Native) |
| :--- | :--- | :--- |
| `media_refs` | `http://192.168.4.1/media/...` | `https://<bucket>.s3.amazonaws.com/...` |
| `node_id` | Implicit from topic | Explicit in payload body |
| `uplink_status` | Not present | `CLOUD_CONNECTED` / `CLOUD_DISCONNECTED` |
| `firmware_version` | Not present | Tracks deployed edge version |

---

## 5. Migration Checklist

- [ ] Provision a HiveMQ Cloud cluster and create node credentials
- [ ] Set environment variables on the Raspberry Pi (`MQTT_CLOUD_*`)
- [ ] Create a cloud storage bucket with appropriate IAM permissions
- [ ] Deploy updated `sentinel_node.py` (v2.0) to the Pi
- [ ] Verify MQTT connectivity from Pi to cloud broker
- [ ] Verify image upload and pre-signed URL generation
- [ ] Update the mobile app's MQTT client to connect to the cloud broker
- [ ] Decommission local Mosquitto and Nginx services on the Pi
- [ ] Run end-to-end test: Camera trigger → Cloud alert → Mobile notification

---

*RootsSecure Cloud Architecture Contract — Maintained by the Edge Engineering Team*
