# JCB + Construction-PPE Training Execution Plan

This is the exact plan to train a detector for your pipeline using:

- JCB dataset: `dataclusterlabs/jcb-image-dataset` (Kaggle)
- PPE dataset: `construction-ppe` (Ultralytics)

## 1) Models I will use

- Primary edge model: `yolo26n.pt`
  - Reason: newest Ultralytics edge-focused nano model, fast for Raspberry Pi class targets.
- Baseline comparison model: `yolo11n.pt`
  - Reason: stable baseline to ensure we are not regressing.
- Optional higher-accuracy reference: `yolo26s.pt`
  - Reason: sanity-check upper bound if nano models underfit.

## 2) Environment setup

```powershell
cd D:\fu\algo_main-main
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install ultralytics kaggle pyyaml
```

Set Kaggle API credentials (`%USERPROFILE%\.kaggle\kaggle.json`) first.

## 3) Download datasets

### 3.1 Kaggle JCB dataset

```powershell
mkdir datasets\raw -Force
kaggle datasets download -d dataclusterlabs/jcb-image-dataset -p datasets\raw --unzip
```

### 3.2 Construction-PPE dataset

Ultralytics auto-downloads this dataset when first used:

```powershell
yolo detect train data=construction-ppe.yaml model=yolo26n.pt epochs=1 imgsz=640
```

## 4) Dataset normalization and merge

You must convert both datasets into one YOLO-detect layout:

```text
datasets\merged_jcb_ppe\
  images\train
  images\val
  images\test
  labels\train
  labels\val
  labels\test
  data.yaml
```

### 4.1 Target class map (fixed IDs)

Use this exact class list so training and inference stay consistent:

```yaml
names:
  0: jcb
  1: helmet
  2: gloves
  3: vest
  4: boots
  5: goggles
  6: none
  7: person
  8: no_helmet
  9: no_goggle
  10: no_gloves
  11: no_boots
```

Important:
- Construction-PPE uses `Person` (capital P) in upstream YAML. Normalize to lowercase `person`.
- If JCB dataset is classification-only (no bounding boxes), do not mix it directly in detect training until you generate bounding-box labels.

### 4.2 Merge strategy

- Keep original train/val/test splits when available.
- If JCB has no split, use `80/10/10` random split with `seed=42`.
- Oversample JCB in train split if it is much smaller than PPE.
  - Recommended start: `2x` replication of JCB train images.

## 5) Training runs (exact)

Run all three, then keep the best by `mAP50-95`, recall for `jcb`, and edge latency.

### Run A (primary): YOLO26n + AdamW

```powershell
yolo detect train `
  model=yolo26n.pt `
  data=datasets/merged_jcb_ppe/data.yaml `
  epochs=120 `
  imgsz=640 `
  batch=16 `
  optimizer=AdamW `
  lr0=0.001 `
  lrf=0.01 `
  weight_decay=0.0005 `
  momentum=0.937 `
  warmup_epochs=3.0 `
  warmup_momentum=0.8 `
  warmup_bias_lr=0.1 `
  box=7.5 `
  cls=0.5 `
  dfl=1.5 `
  hsv_h=0.015 `
  hsv_s=0.7 `
  hsv_v=0.4 `
  degrees=5.0 `
  translate=0.1 `
  scale=0.5 `
  shear=1.0 `
  perspective=0.0 `
  flipud=0.0 `
  fliplr=0.5 `
  mosaic=1.0 `
  mixup=0.1 `
  close_mosaic=10 `
  cos_lr=True `
  patience=30 `
  amp=True `
  workers=8 `
  device=0 `
  seed=42 `
  deterministic=True `
  project=runs/jcb_ppe `
  name=yolo26n_adamw
```

### Run B (comparison): YOLO26n + SGD

```powershell
yolo detect train `
  model=yolo26n.pt `
  data=datasets/merged_jcb_ppe/data.yaml `
  epochs=120 imgsz=640 batch=16 `
  optimizer=SGD lr0=0.01 lrf=0.01 momentum=0.937 weight_decay=0.0005 `
  warmup_epochs=3.0 warmup_momentum=0.8 warmup_bias_lr=0.1 `
  box=7.5 cls=0.5 dfl=1.5 `
  mosaic=1.0 mixup=0.1 close_mosaic=10 cos_lr=True patience=30 `
  amp=True workers=8 device=0 seed=42 deterministic=True `
  project=runs/jcb_ppe name=yolo26n_sgd
```

### Run C (baseline): YOLO11n + AdamW

```powershell
yolo detect train `
  model=yolo11n.pt `
  data=datasets/merged_jcb_ppe/data.yaml `
  epochs=120 imgsz=640 batch=16 `
  optimizer=AdamW lr0=0.001 lrf=0.01 weight_decay=0.0005 momentum=0.937 `
  warmup_epochs=3.0 warmup_momentum=0.8 warmup_bias_lr=0.1 `
  box=7.5 cls=0.5 dfl=1.5 `
  mosaic=1.0 mixup=0.1 close_mosaic=10 cos_lr=True patience=30 `
  amp=True workers=8 device=0 seed=42 deterministic=True `
  project=runs/jcb_ppe name=yolo11n_adamw
```

## 6) Validation and model selection

```powershell
yolo detect val model=runs/jcb_ppe/yolo26n_adamw/weights/best.pt data=datasets/merged_jcb_ppe/data.yaml split=test
yolo detect val model=runs/jcb_ppe/yolo26n_sgd/weights/best.pt   data=datasets/merged_jcb_ppe/data.yaml split=test
yolo detect val model=runs/jcb_ppe/yolo11n_adamw/weights/best.pt data=datasets/merged_jcb_ppe/data.yaml split=test
```

Selection priority:
1. `jcb` recall
2. overall `mAP50-95`
3. latency on target edge hardware

## 7) Export for edge deployment

Use your winning model checkpoint (`best.pt`):

```powershell
yolo export model=runs/jcb_ppe/yolo26n_adamw/weights/best.pt format=ncnn imgsz=640
```

Optional INT8 (after calibration support is ready in your deployment path):

```powershell
yolo export model=runs/jcb_ppe/yolo26n_adamw/weights/best.pt format=ncnn int8=True data=datasets/merged_jcb_ppe/data.yaml
```

## 8) Integration note for this repository

Your edge logic currently uses hardcoded class IDs in:
- `sentinel_edge/logic/rules.py`

If your final class order differs, update rules to use class names from model metadata instead of fixed integer IDs. This prevents silent logic errors.

## 9) Expected outputs

- Trained weights:
  - `runs/jcb_ppe/<run_name>/weights/best.pt`
- Training curves and confusion matrix:
  - `runs/jcb_ppe/<run_name>/`
- Edge export artifacts:
  - `best_ncnn_model/` (`.param` + `.bin`)

## 10) Quick decision recommendation

If you want one run first (fastest path), do:
- `Run A: yolo26n + AdamW` with the parameters above.

