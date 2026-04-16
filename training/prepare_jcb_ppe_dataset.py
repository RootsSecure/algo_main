from __future__ import annotations

import argparse
import json
import random
import shutil
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

# Final unified class list used by merged YOLO dataset.
CLASS_NAMES = [
    "jcb",
    "helmet",
    "gloves",
    "vest",
    "boots",
    "goggles",
    "none",
    "person",
    "no_helmet",
    "no_goggle",
    "no_gloves",
    "no_boots",
]

# construction-ppe original id -> merged id (jcb inserted at 0)
PPE_CLASS_REMAP = {
    0: 1,   # helmet
    1: 2,   # gloves
    2: 3,   # vest
    3: 4,   # boots
    4: 5,   # goggles
    5: 6,   # none
    6: 7,   # Person -> person
    7: 8,   # no_helmet
    8: 9,   # no_goggle
    9: 10,  # no_gloves
    10: 11, # no_boots
}

# Known JCB label variants in Pascal VOC XML.
JCB_NAMES = {"jcb", "excavator", "backhoe", "backhoe_loader"}


@dataclass
class Counts:
    ppe_images: int = 0
    ppe_labels_written: int = 0
    ppe_labels_skipped: int = 0
    jcb_images_total: int = 0
    jcb_images_used: int = 0
    jcb_images_missing_xml: int = 0
    jcb_images_without_boxes: int = 0
    jcb_boxes_written: int = 0


def safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def reset_merged_dirs(merged_root: Path) -> None:
    if merged_root.exists():
        shutil.rmtree(merged_root)
    for split in ("train", "val", "test"):
        safe_mkdir(merged_root / "images" / split)
        safe_mkdir(merged_root / "labels" / split)


def list_images(path: Path) -> list[Path]:
    return sorted([p for p in path.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS])


def write_data_yaml(merged_root: Path) -> None:
    yaml_path = merged_root / "data.yaml"
    names_block = "\n".join([f"  {idx}: {name}" for idx, name in enumerate(CLASS_NAMES)])
    yaml_text = (
        f"path: {merged_root.as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n"
        "names:\n"
        f"{names_block}\n"
    )
    yaml_path.write_text(yaml_text, encoding="utf-8")


def remap_ppe_label_line(line: str) -> str | None:
    parts = line.strip().split()
    if len(parts) != 5:
        return None
    try:
        cls = int(parts[0])
        mapped = PPE_CLASS_REMAP[cls]
        coords = [float(v) for v in parts[1:]]
    except Exception:
        return None
    return f"{mapped} {coords[0]:.6f} {coords[1]:.6f} {coords[2]:.6f} {coords[3]:.6f}"


def copy_ppe_split(raw_ppe: Path, merged_root: Path, split: str, counts: Counts) -> None:
    src_img_dir = raw_ppe / "images" / split
    src_lbl_dir = raw_ppe / "labels" / split
    dst_img_dir = merged_root / "images" / split
    dst_lbl_dir = merged_root / "labels" / split

    for img_path in list_images(src_img_dir):
        out_stem = f"ppe_{img_path.stem}"
        out_img_path = dst_img_dir / f"{out_stem}{img_path.suffix.lower()}"
        out_lbl_path = dst_lbl_dir / f"{out_stem}.txt"
        shutil.copy2(img_path, out_img_path)
        counts.ppe_images += 1

        src_lbl_path = src_lbl_dir / f"{img_path.stem}.txt"
        if not src_lbl_path.exists():
            out_lbl_path.write_text("", encoding="utf-8")
            continue

        out_lines: list[str] = []
        for raw_line in src_lbl_path.read_text(encoding="utf-8").splitlines():
            mapped = remap_ppe_label_line(raw_line)
            if mapped is None:
                counts.ppe_labels_skipped += 1
                continue
            out_lines.append(mapped)
            counts.ppe_labels_written += 1
        out_lbl_path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")


def parse_voc_jcb_boxes(xml_path: Path) -> tuple[int, int, list[tuple[float, float, float, float]]]:
    root = ET.parse(xml_path).getroot()

    size = root.find("size")
    if size is None:
        return 0, 0, []
    width = int(float(size.findtext("width", default="0")))
    height = int(float(size.findtext("height", default="0")))
    if width <= 1 or height <= 1:
        return 0, 0, []

    boxes: list[tuple[float, float, float, float]] = []
    for obj in root.findall("object"):
        label = (obj.findtext("name", default="") or "").strip().lower()
        if label not in JCB_NAMES:
            continue
        bnd = obj.find("bndbox")
        if bnd is None:
            continue
        try:
            xmin = float(bnd.findtext("xmin", default="0"))
            ymin = float(bnd.findtext("ymin", default="0"))
            xmax = float(bnd.findtext("xmax", default="0"))
            ymax = float(bnd.findtext("ymax", default="0"))
        except Exception:
            continue
        xmin = max(0.0, min(xmin, width - 1))
        ymin = max(0.0, min(ymin, height - 1))
        xmax = max(0.0, min(xmax, width - 1))
        ymax = max(0.0, min(ymax, height - 1))
        if xmax <= xmin or ymax <= ymin:
            continue
        boxes.append((xmin, ymin, xmax, ymax))
    return width, height, boxes


def xyxy_to_yolo(width: int, height: int, xmin: float, ymin: float, xmax: float, ymax: float) -> tuple[float, float, float, float]:
    x_center = ((xmin + xmax) / 2.0) / width
    y_center = ((ymin + ymax) / 2.0) / height
    box_w = (xmax - xmin) / width
    box_h = (ymax - ymin) / height
    return x_center, y_center, box_w, box_h


def split_jcb_images(image_paths: list[Path], seed: int, train_ratio: float, val_ratio: float) -> dict[str, list[Path]]:
    rng = random.Random(seed)
    shuffled = list(image_paths)
    rng.shuffle(shuffled)

    n_total = len(shuffled)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    n_test = n_total - n_train - n_val
    if n_test < 1 and n_total >= 3:
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


def copy_jcb_split(raw_jcb: Path, merged_root: Path, split: str, image_paths: list[Path], counts: Counts) -> None:
    xml_dir = raw_jcb / "Annotations" / "Annotations"
    dst_img_dir = merged_root / "images" / split
    dst_lbl_dir = merged_root / "labels" / split

    for img_path in image_paths:
        counts.jcb_images_total += 1
        xml_path = xml_dir / f"{img_path.stem}.xml"
        if not xml_path.exists():
            counts.jcb_images_missing_xml += 1
            continue

        width, height, boxes = parse_voc_jcb_boxes(xml_path)
        if width <= 1 or height <= 1 or not boxes:
            counts.jcb_images_without_boxes += 1
            continue

        out_stem = f"jcb_{img_path.stem}"
        out_img_path = dst_img_dir / f"{out_stem}{img_path.suffix.lower()}"
        out_lbl_path = dst_lbl_dir / f"{out_stem}.txt"
        shutil.copy2(img_path, out_img_path)

        lines: list[str] = []
        for xmin, ymin, xmax, ymax in boxes:
            x, y, w, h = xyxy_to_yolo(width, height, xmin, ymin, xmax, ymax)
            lines.append(f"0 {x:.6f} {y:.6f} {w:.6f} {h:.6f}")
            counts.jcb_boxes_written += 1

        out_lbl_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        counts.jcb_images_used += 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare merged YOLO dataset from JCB VOC XML + Construction-PPE.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    raw_ppe = repo_root / "datasets" / "raw" / "construction-ppe"
    raw_jcb = repo_root / "datasets" / "raw" / "jcb"
    merged_root = repo_root / "datasets" / "merged_jcb_ppe"
    artifacts_root = repo_root / "training" / "artifacts"

    if not raw_ppe.exists():
        raise FileNotFoundError(f"Missing dataset folder: {raw_ppe}")
    if not raw_jcb.exists():
        raise FileNotFoundError(f"Missing dataset folder: {raw_jcb}")

    reset_merged_dirs(merged_root)
    safe_mkdir(artifacts_root)

    counts = Counts()

    for split in ("train", "val", "test"):
        copy_ppe_split(raw_ppe, merged_root, split, counts)

    jcb_images = list_images(raw_jcb)
    jcb_split = split_jcb_images(jcb_images, args.seed, args.train_ratio, args.val_ratio)
    for split in ("train", "val", "test"):
        copy_jcb_split(raw_jcb, merged_root, split, jcb_split[split], counts)

    write_data_yaml(merged_root)

    summary = {
        "class_names": CLASS_NAMES,
        "counts": counts.__dict__,
        "jcb_split_sizes": {k: len(v) for k, v in jcb_split.items()},
        "merged_root": str(merged_root),
    }
    (artifacts_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

