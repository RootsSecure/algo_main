from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Ultralytics training from YAML config.")
    parser.add_argument("--cfg", required=True, help="Path to training config YAML.")
    parser.add_argument("--device", default=None, help="Override training device, e.g. 0 or cpu.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cfg_path = Path(args.cfg).resolve()
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    model_name = cfg.pop("model")
    cfg.pop("task", None)
    cfg.pop("mode", None)
    if args.device is not None:
        cfg["device"] = args.device

    model = YOLO(model_name)
    model.train(**cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

