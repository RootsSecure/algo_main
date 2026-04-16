# Getting Started

This guide is for someone seeing the project for the first time.

## What this project does

NRI Plot Sentinel is a backend for monitoring vacant land plots. It helps owners, operators, and connected edge devices work together around alerts, incidents, and response workflows.

## Main ideas to learn first

### 1. Property
A vacant plot being monitored.

### 2. Device
A camera or sensor linked to that property.

### 3. Alert
A single incoming event like motion, tamper, offline, or gate breach.

### 4. Incident
A higher-level operational record created from one or more alerts.

### 5. Gateway
A secure connection path for a Raspberry Pi or a normal PC acting as the edge device near the property.

## Suggested reading order

1. `README.md`
2. `docs/product/problem-statement.md`
3. `docs/architecture/system-overview.md`
4. `docs/api/endpoint-catalog.md`
5. `docs/api/raspberry-pi-gateway.md`
6. `tests/api/test_api_flow.py`
7. `tests/api/test_gateway_flow.py`

## Suggested first commands

```powershell
.\nri_proj\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py test
python manage.py run
```

## What to explore next

- Open `/docs` for API docs
- Open `/project-docs` for the markdown docs index
- Read the tests to see the expected happy paths
