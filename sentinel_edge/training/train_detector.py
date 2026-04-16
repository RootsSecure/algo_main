from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from sentinel_edge.training.prepare_composite_dataset import DEFAULT_OUTPUT_ROOT, prepare_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the Sentinel Edge object detector.")
    parser.add_argument("--jcb-root", type=Path, default=Path(r"D:\Nri Dataset\Jcb"))
    parser.add_argument("--tractor-root", type=Path, default=Path(r"D:\Nri Dataset\Tractor Truck"))
    parser.add_argument(
        "--pedestrian-root",
        type=Path,
        default=Path(r"D:\Nri Dataset\Pedestrain\Indian-Pedestrian-Intention-Dataset-main"),
    )
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--prepare", action="store_true", help="Rebuild the YOLO dataset before training.")
    parser.add_argument("--force-prepare", action="store_true", help="Overwrite an existing prepared dataset.")
    parser.add_argument("--pedestrian-stride", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=8)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--patience", type=int, default=20)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1] / "artifacts" / "runs")
    parser.add_argument("--name", default="nri-directml")
    parser.add_argument("--pretrained", action="store_true", help="Use pretrained weights when the selected model supports them.")
    parser.add_argument("--validate", action="store_true", help="Run validation during training.")
    parser.add_argument(
        "--device",
        choices=("auto", "directml", "cpu", "cuda"),
        default="directml",
        help="Preferred training backend.",
    )
    parser.add_argument("--export-ncnn", action="store_true", help="Export the best checkpoint to NCNN after training.")
    return parser.parse_args()


def resolve_training_device(device_name: str):
    amp = True
    device_arg = "cpu"
    extra = {}

    if device_name == "directml":
        import torch_directml

        device_arg = torch_directml.device()
        amp = False
        extra["backend"] = "directml"
        extra["torch_device"] = str(device_arg)
    elif device_name == "cuda":
        device_arg = "0"
        extra["backend"] = "cuda"
    elif device_name == "cpu":
        device_arg = "cpu"
        amp = False
        extra["backend"] = "cpu"
    else:
        extra["backend"] = "auto"
        device_arg = "0"

    return device_arg, amp, extra


def patch_ultralytics_for_directml() -> None:
    import torch
    from ultralytics.engine import trainer as ultralytics_trainer
    from ultralytics.utils import loss as ultralytics_loss
    from ultralytics.utils import tal as ultralytics_tal

    def directml_preprocess(self, targets: torch.Tensor, batch_size: int, scale_tensor: torch.Tensor) -> torch.Tensor:
        nl, ne = targets.shape
        if nl == 0:
            return torch.zeros(batch_size, 0, ne - 1, device=self.device)

        batch_idx = targets[:, 0].long()
        batch_idx_cpu = batch_idx.to("cpu")
        counts_cpu = torch.bincount(batch_idx_cpu, minlength=batch_size)
        max_targets = int(counts_cpu.max().item()) if counts_cpu.numel() else 0

        out = torch.zeros(batch_size, max_targets, ne - 1, device=self.device)
        within_idx_cpu = torch.empty(nl, dtype=torch.long)
        seen = torch.zeros(batch_size, dtype=torch.long)

        for i, image_idx in enumerate(batch_idx_cpu.tolist()):
            within_idx_cpu[i] = seen[image_idx]
            seen[image_idx] += 1

        out[batch_idx, within_idx_cpu.to(self.device)] = targets[:, 1:]
        out[..., 1:5] = ultralytics_loss.xywh2xyxy(out[..., 1:5].mul_(scale_tensor))
        return out

    def directml_select_topk_candidates(self, metrics, topk_mask=None):
        metrics_cpu = metrics.to("cpu")
        topk_metrics_cpu, topk_idxs_cpu = torch.topk(metrics_cpu, self.topk, dim=-1, largest=True)
        if topk_mask is None:
            topk_mask_cpu = (topk_metrics_cpu.max(-1, keepdim=True)[0] > self.eps).expand_as(topk_idxs_cpu)
        else:
            topk_mask_cpu = topk_mask.to("cpu")

        topk_idxs_cpu.masked_fill_(~topk_mask_cpu, 0)
        count_tensor_cpu = torch.zeros(metrics_cpu.shape, dtype=torch.int8)
        ones_cpu = torch.ones_like(topk_idxs_cpu[:, :, :1], dtype=torch.int8)
        for k in range(self.topk):
            count_tensor_cpu.scatter_add_(-1, topk_idxs_cpu[:, :, k : k + 1], ones_cpu)
        count_tensor_cpu.masked_fill_(count_tensor_cpu > 1, 0)
        return count_tensor_cpu.to(device=metrics.device, dtype=metrics.dtype)

    def directml_get_memory(self, fraction=False):
        return 0.0

    def directml_clear_memory(self, threshold=None):
        import gc

        gc.collect()
        return None

    def directml_validate(self):
        if getattr(self.args, "val", True):
            return self.validator(self)
        return {}, 0.0

    def directml_final_eval(self):
        model = self.best if self.best.exists() else None
        with ultralytics_trainer.torch_distributed_zero_first(ultralytics_trainer.LOCAL_RANK):
            if ultralytics_trainer.RANK in {-1, 0}:
                ckpt = ultralytics_trainer.strip_optimizer(self.last) if self.last.exists() else {}
                if model:
                    ultralytics_trainer.strip_optimizer(self.best, updates={"train_results": ckpt.get("train_results")})

        should_validate = getattr(self.args, "val", True)
        device_text = str(getattr(self.args, "device", ""))
        is_directml = "privateuseone" in device_text or "directml" in device_text

        if model and should_validate and not is_directml:
            ultralytics_trainer.LOGGER.info(f"\nValidating {model}...")
            self.validator.args.plots = self.args.plots
            self.validator.args.compile = False
            self.metrics = self.validator(model=model)
            self.metrics.pop("fitness", None)
            self.run_callbacks("on_fit_epoch_end")
        elif model:
            ultralytics_trainer.LOGGER.info(f"\nSkipping final validation for device={device_text or 'unknown'}.")

    ultralytics_loss.v8DetectionLoss.preprocess = directml_preprocess
    ultralytics_tal.TaskAlignedAssigner.select_topk_candidates = directml_select_topk_candidates
    ultralytics_trainer.BaseTrainer._get_memory = directml_get_memory
    ultralytics_trainer.BaseTrainer._clear_memory = directml_clear_memory
    ultralytics_trainer.BaseTrainer.validate = directml_validate
    ultralytics_trainer.BaseTrainer.final_eval = directml_final_eval


def resolve_run_dir(project_root: Path, run_name: str) -> Path | None:
    candidates = sorted(project_root.glob(f"{run_name}*"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


def main() -> None:
    args = parse_args()
    config_root = Path(__file__).resolve().parents[1] / "artifacts" / "ultralytics_config"
    matplotlib_root = Path(__file__).resolve().parents[1] / "artifacts" / "matplotlib"
    config_root.mkdir(parents=True, exist_ok=True)
    matplotlib_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("YOLO_CONFIG_DIR", str(config_root))
    os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_root))

    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise SystemExit(
            "ultralytics is not installed in this environment. Install the DirectML training requirements first."
        ) from exc

    if args.device == "directml":
        patch_ultralytics_for_directml()

    if args.prepare or not (args.dataset_root / "dataset.yaml").exists():
        dataset_yaml, summary = prepare_dataset(
            jcb_root=args.jcb_root,
            tractor_root=args.tractor_root,
            pedestrian_root=args.pedestrian_root,
            output_root=args.dataset_root,
            pedestrian_stride=args.pedestrian_stride,
            seed=args.seed,
            train_ratio=0.8,
            val_ratio=0.1,
            force=args.force_prepare or args.prepare,
        )
    else:
        dataset_yaml = args.dataset_root / "dataset.yaml"
        summary_path = args.dataset_root / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else {}

    device_arg, amp, device_meta = resolve_training_device(args.device)
    print("Training configuration:")
    print(
        json.dumps(
            {
                "dataset_yaml": str(dataset_yaml),
                "device": device_meta,
                "epochs": args.epochs,
                "imgsz": args.imgsz,
                "batch": args.batch,
                "summary": summary,
            },
            indent=2,
        )
    )

    model = YOLO(args.model)
    results = model.train(
        data=str(dataset_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=args.workers,
        patience=args.patience,
        project=str(args.project),
        name=args.name,
        device=device_arg,
        amp=amp,
        pretrained=args.pretrained,
        cache=False,
        val=args.validate,
    )

    save_dir = getattr(results, "save_dir", None)
    if save_dir is None:
        run_dir = resolve_run_dir(args.project, args.name)
    else:
        run_dir = Path(save_dir)

    if run_dir is None:
        raise SystemExit("Training finished, but the run directory could not be resolved.")

    best = run_dir / "weights" / "best.pt"
    last = run_dir / "weights" / "last.pt"
    chosen = best if best.exists() else last
    print(f"Training finished. Checkpoint: {chosen}")

    if args.export_ncnn and chosen.exists():
        exported_model = YOLO(str(chosen))
        exported_path = exported_model.export(format="ncnn", imgsz=args.imgsz)
        print(f"Exported NCNN model: {exported_path}")


if __name__ == "__main__":
    main()
