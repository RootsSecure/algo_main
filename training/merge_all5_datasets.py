from __future__ import annotations

import argparse
import json
import random
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import yaml


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
SOURCE_DATASETS = ["data1", "data2", "data3", "data4", "data5"]


@dataclass
class Sample:
    dataset: str
    image_path: Path
    label_path: Path | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Merge data1..data5 into one YOLO detect dataset with fresh split.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    return parser.parse_args()


def canonicalize_class(name: str) -> str:
    raw = name.strip().lower().replace("-", "_").replace(" ", "_")
    synonyms = {
        "hard_hat": "helmet",
        "hi_viz_helmet": "helmet",
        "hi_viz_vest": "vest",
        "safety_vest": "vest",
        "hi_vis": "vest",
        "digger": "jcb",
        "excavator": "jcb",
        "dumper_truck": "dump_truck",
        "mobile_crane": "crane",
    }
    return synonyms.get(raw, raw)


def ensure_dirs(root: Path) -> None:
    if root.exists():
        shutil.rmtree(root)
    for split in ("train", "val", "test"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)


def load_names(dataset_root: Path) -> list[str]:
    cfg_path = dataset_root / "data.yaml"
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    names = cfg.get("names", [])
    if isinstance(names, dict):
        ordered = [names[k] for k in sorted(names)]
        return [str(x) for x in ordered]
    return [str(x) for x in names]


def find_split_image_dirs(dataset_root: Path) -> list[tuple[str, Path, Path]]:
    candidates: list[tuple[str, str]] = [
        ("train", "train"),
        ("val", "val"),
        ("val", "valid"),
        ("test", "test"),
    ]
    found: list[tuple[str, Path, Path]] = []
    for out_split, folder in candidates:
        img_dir = dataset_root / folder / "images"
        lbl_dir = dataset_root / folder / "labels"
        if img_dir.exists():
            found.append((out_split, img_dir, lbl_dir))
    return found


def collect_samples(dataset_name: str, dataset_root: Path) -> list[Sample]:
    samples: list[Sample] = []
    split_dirs = find_split_image_dirs(dataset_root)
    for _, img_dir, lbl_dir in split_dirs:
        for img_path in sorted(img_dir.iterdir()):
            if not img_path.is_file() or img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            samples.append(
                Sample(
                    dataset=dataset_name,
                    image_path=img_path,
                    label_path=lbl_path if lbl_path.exists() else None,
                )
            )
    return samples


def split_samples(samples: list[Sample], seed: int, train_ratio: float, val_ratio: float) -> dict[str, list[Sample]]:
    rng = random.Random(seed)
    shuffled = list(samples)
    rng.shuffle(shuffled)
    n = len(shuffled)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    n_test = n - n_train - n_val
    if n_test < 1 and n >= 3:
        n_test = 1
        if n_train > n_val:
            n_train -= 1
        else:
            n_val -= 1
    return {
        "train": shuffled[:n_train],
        "val": shuffled[n_train : n_train + n_val],
        "test": shuffled[n_train + n_val :],
    }


def parse_yolo_label_line(line: str) -> tuple[int, float, float, float, float] | None:
    parts = line.strip().split()
    if len(parts) != 5:
        return None
    try:
        cls = int(parts[0])
        x, y, w, h = [float(v) for v in parts[1:]]
    except Exception:
        return None
    return cls, x, y, w, h


def write_data_yaml(merged_root: Path, class_names: list[str]) -> None:
    lines = [
        f"path: {merged_root.as_posix()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "names:",
    ]
    lines.extend([f"  {idx}: {name}" for idx, name in enumerate(class_names)])
    (merged_root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    raw_root = repo_root / "datasets" / "raw"
    merged_root = repo_root / "datasets" / "merged_all5"
    artifacts = repo_root / "training" / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)

    ensure_dirs(merged_root)

    dataset_name_lists: dict[str, list[str]] = {}
    dataset_samples: dict[str, list[Sample]] = {}
    for name in SOURCE_DATASETS:
        ds_root = raw_root / name
        if not ds_root.exists():
            raise FileNotFoundError(f"Missing expected dataset: {ds_root}")
        dataset_name_lists[name] = load_names(ds_root)
        dataset_samples[name] = collect_samples(name, ds_root)

    # Build unified class map in deterministic dataset order.
    global_class_to_id: dict[str, int] = {}
    global_classes: list[str] = []
    per_dataset_id_map: dict[str, dict[int, int]] = {}
    for ds_name in SOURCE_DATASETS:
        per_dataset_id_map[ds_name] = {}
        for idx, class_name in enumerate(dataset_name_lists[ds_name]):
            canonical = canonicalize_class(class_name)
            if canonical not in global_class_to_id:
                global_class_to_id[canonical] = len(global_classes)
                global_classes.append(canonical)
            per_dataset_id_map[ds_name][idx] = global_class_to_id[canonical]

    # Re-split each dataset into train/val/test to ensure all splits exist.
    merged_split_samples: dict[str, list[Sample]] = {"train": [], "val": [], "test": []}
    per_dataset_split_counts: dict[str, dict[str, int]] = {}
    for ds_name in SOURCE_DATASETS:
        split = split_samples(dataset_samples[ds_name], args.seed, args.train_ratio, args.val_ratio)
        per_dataset_split_counts[ds_name] = {k: len(v) for k, v in split.items()}
        for k in ("train", "val", "test"):
            merged_split_samples[k].extend(split[k])

    # Write files.
    stats = {
        "source_datasets": SOURCE_DATASETS,
        "global_classes": global_classes,
        "global_class_count": len(global_classes),
        "per_dataset_split_counts": per_dataset_split_counts,
        "merged_split_counts": {k: len(v) for k, v in merged_split_samples.items()},
        "images_copied": 0,
        "labels_written": 0,
        "label_lines_written": 0,
        "invalid_label_lines_skipped": 0,
        "missing_label_files": 0,
    }

    counters = defaultdict(int)
    for split_name in ("train", "val", "test"):
        for sample in merged_split_samples[split_name]:
            counters[(sample.dataset, split_name)] += 1
            idx = counters[(sample.dataset, split_name)]
            out_stem = f"{sample.dataset}_{split_name}_{idx:06d}"
            out_img = merged_root / "images" / split_name / f"{out_stem}{sample.image_path.suffix.lower()}"
            out_lbl = merged_root / "labels" / split_name / f"{out_stem}.txt"
            shutil.copy2(sample.image_path, out_img)
            stats["images_copied"] += 1

            out_lines: list[str] = []
            if sample.label_path is None:
                stats["missing_label_files"] += 1
            else:
                for line in sample.label_path.read_text(encoding="utf-8").splitlines():
                    parsed = parse_yolo_label_line(line)
                    if parsed is None:
                        stats["invalid_label_lines_skipped"] += 1
                        continue
                    src_cls, x, y, w, h = parsed
                    mapped = per_dataset_id_map[sample.dataset].get(src_cls)
                    if mapped is None:
                        stats["invalid_label_lines_skipped"] += 1
                        continue
                    out_lines.append(f"{mapped} {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
                    stats["label_lines_written"] += 1

            out_lbl.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
            stats["labels_written"] += 1

    write_data_yaml(merged_root, global_classes)
    summary_path = artifacts / "merged_all5_summary.json"
    summary_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

