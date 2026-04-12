import time
import requests

def get_cpu_temp():
    """Reads CPU temperature from Raspberry Pi sysfs."""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            return float(f.read().strip()) / 1000.0
    except Exception:
        return 45.0 # Fallback for non-Pi environments/dev machines

def measure_latency(url):
    """Measures network latency to the backend endpoint."""
    try:
        start = time.time()
        # OPTIONS request is usually extremely lightweight and supported by CORS/Gateways
        requests.options(url, timeout=5)
        return int((time.time() - start) * 1000)
    except Exception:
        return -1 # -1 denotes offline/unreachable
