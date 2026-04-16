from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml
from ultralytics import YOLO


def load_cfg(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def split_model_and_kwargs(cfg: dict, device_override: str | None) -> tuple[str, dict]:
    cfg = dict(cfg)
    model_name = str(cfg.pop("model"))
    cfg.pop("task", None)
    cfg.pop("mode", None)
    if device_override is not None:
        cfg["device"] = device_override
    return model_name, cfg


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Automated two-phase training for merged_all5 dataset.")
    p.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--phase1-cfg", type=Path, default=Path("training/configs/all5_phase1_yolo26n_adamw.yaml"))
    p.add_argument("--phase2-cfg", type=Path, default=Path("training/configs/all5_phase2_yolo26n_sgd.yaml"))
    p.add_argument("--device", type=str, default="0")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    phase1_cfg_path = (repo_root / args.phase1_cfg).resolve()
    phase2_cfg_path = (repo_root / args.phase2_cfg).resolve()
    artifacts_dir = (repo_root / "training" / "artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    phase1_cfg = load_cfg(phase1_cfg_path)
    phase2_cfg = load_cfg(phase2_cfg_path)

    phase1_model_name, phase1_kwargs = split_model_and_kwargs(phase1_cfg, args.device)
    print("Starting Phase 1 with model:", phase1_model_name)
    phase1_model = YOLO(phase1_model_name)
    phase1_model.train(**phase1_kwargs)

    if phase1_model.trainer is None or phase1_model.trainer.best is None:
        raise RuntimeError("Phase 1 completed but best checkpoint path not found.")
    phase1_best = Path(str(phase1_model.trainer.best)).resolve()
    print("Phase 1 best:", phase1_best)

    phase2_model_name, phase2_kwargs = split_model_and_kwargs(phase2_cfg, args.device)
    # Always use phase1 best checkpoint for phase2 regardless of static YAML placeholder.
    phase2_model_name = str(phase1_best)
    print("Starting Phase 2 with model:", phase2_model_name)
    phase2_model = YOLO(phase2_model_name)
    phase2_model.train(**phase2_kwargs)

    if phase2_model.trainer is None or phase2_model.trainer.best is None:
        raise RuntimeError("Phase 2 completed but best checkpoint path not found.")
    phase2_best = Path(str(phase2_model.trainer.best)).resolve()
    print("Phase 2 best:", phase2_best)

    summary = {
        "phase1_best": str(phase1_best),
        "phase2_best": str(phase2_best),
        "phase1_cfg": str(phase1_cfg_path),
        "phase2_cfg": str(phase2_cfg_path),
    }
    summary_path = artifacts_dir / "all5_two_phase_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("Summary written to:", summary_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

