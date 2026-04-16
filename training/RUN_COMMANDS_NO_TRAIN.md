# Runbook (Prepared, Not Started)

This file contains all commands needed after review. No training has been started.

## 1) Build merged dataset (safe to run now)

```powershell
cd D:\fu\algo_main-main
python training\prepare_jcb_ppe_dataset.py
```

## 2) Inspect generated artifacts

```powershell
Get-Content training\artifacts\dataset_summary.json
Get-Content datasets\merged_jcb_ppe\data.yaml
```

## 3) Two-stage training plan (only run when you say start)

### Phase 1: AdamW initialization

```powershell
yolo detect train cfg=training/configs/jcb_ppe_phase1_yolo26n_adamw.yaml device=0
```

### Phase 2: SGD + momentum finalization

```powershell
yolo detect train cfg=training/configs/jcb_ppe_phase2_yolo26n_sgd.yaml device=0
```

## 4) Alternate single-run baseline (optional)

### YOLO26n + SGD

```powershell
yolo detect train `
  model=yolo26n.pt data=datasets/merged_jcb_ppe/data.yaml `
  epochs=120 imgsz=640 batch=16 `
  optimizer=SGD lr0=0.01 lrf=0.01 momentum=0.937 weight_decay=0.0005 `
  warmup_epochs=3.0 warmup_momentum=0.8 warmup_bias_lr=0.1 `
  box=7.5 cls=0.5 dfl=1.5 `
  mosaic=1.0 mixup=0.1 close_mosaic=10 cos_lr=True patience=30 `
  amp=True workers=8 seed=42 deterministic=True `
  project=runs/jcb_ppe name=yolo26n_sgd device=0
```

### YOLO11n + AdamW baseline

```powershell
yolo detect train `
  model=yolo11n.pt data=datasets/merged_jcb_ppe/data.yaml `
  epochs=120 imgsz=640 batch=16 `
  optimizer=AdamW lr0=0.001 lrf=0.01 momentum=0.937 weight_decay=0.0005 `
  warmup_epochs=3.0 warmup_momentum=0.8 warmup_bias_lr=0.1 `
  box=7.5 cls=0.5 dfl=1.5 `
  mosaic=1.0 mixup=0.1 close_mosaic=10 cos_lr=True patience=30 `
  amp=True workers=8 seed=42 deterministic=True `
  project=runs/jcb_ppe name=yolo11n_adamw device=0
```

## 5) Validation commands (after phase 2)

```powershell
yolo detect val model=runs/jcb_ppe/phase1_adamw/weights/best.pt data=datasets/merged_jcb_ppe/data.yaml split=test device=0
yolo detect val model=runs/jcb_ppe/phase2_sgd/weights/best.pt   data=datasets/merged_jcb_ppe/data.yaml split=test device=0
```

## 6) Edge export (recommended safe order)

### 6.1 Export FP NCNN first (stability baseline)

```powershell
yolo export model=runs/jcb_ppe/phase2_sgd/weights/best.pt format=ncnn imgsz=640
```

### 6.2 Export INT8 NCNN next (only if accuracy drop is acceptable)

```powershell
yolo export model=runs/jcb_ppe/phase2_sgd/weights/best.pt format=ncnn int8=True data=datasets/merged_jcb_ppe/data.yaml
```
