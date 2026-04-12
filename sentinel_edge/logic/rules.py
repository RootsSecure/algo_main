import time
import math

class AlertEvent:
    def __init__(self, type_name, level, metadata):
        self.type = type_name
        self.level = level
        self.metadata = metadata
        self.id = f"evt_{type_name}_{int(time.time()*1000)}"

def do_boxes_overlap(box1, box2, variance=0.10):
    """
    Checks if an object is 'stationary' by ensuring the centroid movement
    and size changes are within a strict variance threshold (e.g. 10%).
    This ignores small camera vibrations or wind.
    """
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    cx1, cy1 = x1 + w1/2.0, y1 + h1/2.0
    cx2, cy2 = x2 + w2/2.0, y2 + h2/2.0
    
    # Calculate dimensional scaling baseline using the original box
    max_drift_x = w1 * variance
    max_drift_y = h1 * variance
    max_size_diff = (w1 * h1) * variance
    
    # Check if centroids migrated more than the allowed horizontal/vertical drift
    if abs(cx1 - cx2) > max_drift_x or abs(cy1 - cy2) > max_drift_y:
        return False
        
    # Check if the bounding box drastically changed size (depth movement)
    area1 = w1 * h1
    area2 = w2 * h2
    if abs(area1 - area2) > max_size_diff:
        return False
        
    return True

class SentinelLogicEngine:
    """Heuristic Logic to detect complex patterns from raw bounding boxes."""
    def __init__(self):
        self.jcb_frames = 0
        
        self.tractor_cache = None  # {first_seen: float, box: list, alerted_5m: bool}
        self.tractor_timeout = 15.0 # seconds before tractor cache is cleared if unseen

    def evaluate(self, detections):
        alerts = []
        
        has_jcb = False
        has_tractor = False
        has_person_or_shovel = False
        
        current_tractor_box = None

        for d in detections:
            cid = d['class']
            if cid == 1: # jcb
                has_jcb = True
            elif cid == 4: # tractor
                has_tractor = True
                current_tractor_box = d['bbox']
            elif cid in [0, 2, 5]:  # person, worker, shovel
                has_person_or_shovel = True

        # ----------------------------------------------------
        # Rule 1: Illegal Construction (JCB >= 5 frames)
        # ----------------------------------------------------
        if has_jcb:
            self.jcb_frames += 1
            if self.jcb_frames >= 5:
                alerts.append(AlertEvent(
                    "ILLEGAL_CONSTRUCTION", 
                    "CRITICAL", 
                    {"reason": "JCB actively detected"}
                ))
                self.jcb_frames = -10 # cooldown
        else:
            self.jcb_frames = max(0, self.jcb_frames - 1)

        # ----------------------------------------------------
        # Rule 2: Soil Theft (Tractor + Person/Shovel)
        # ----------------------------------------------------
        now = time.time()
        if has_tractor:
            if has_person_or_shovel:
                alerts.append(AlertEvent(
                    "SOIL_THEFT_ACTIVE", 
                    "HIGH", 
                    {"reason": "Tractor and person/shovel associated"}
                ))
            
            # ------------------------------------------------
            # Rule 3: Stationary Escalation (> 5 mins tractor)
            # ------------------------------------------------
            if self.tractor_cache is None:
                self.tractor_cache = {
                    "first_seen": now,
                    "last_seen": now,
                    "box": current_tractor_box,
                    "alerted_5m": False
                }
            else:
                self.tractor_cache["last_seen"] = now
                if do_boxes_overlap(self.tractor_cache["box"], current_tractor_box):
                    duration = now - self.tractor_cache["first_seen"]
                    if duration > 300 and not self.tractor_cache["alerted_5m"]:
                        alerts.append(AlertEvent(
                            "SOIL_THEFT_ESCALATION", 
                            "CRITICAL", 
                            {"reason": "Tractor remained stationary > 5 minutes", "duration_sec": int(duration)}
                        ))
                        self.tractor_cache["alerted_5m"] = True
                else:
                    # Tractor moved, reset cache positional baseline
                    self.tractor_cache = {
                        "first_seen": now,
                        "last_seen": now,
                        "box": current_tractor_box,
                        "alerted_5m": False
                    }
        else:
            # Clear tractor cache if it leaves the frame completely for a timeout period
            if self.tractor_cache and (now - self.tractor_cache["last_seen"] > self.tractor_timeout):
                self.tractor_cache = None

        return alerts
