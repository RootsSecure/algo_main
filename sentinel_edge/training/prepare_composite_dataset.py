from __future__ import annotations

import argparse
import json
import random
import shutil
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

import cv2

CLASS_NAMES = ["person", "jcb", "tractor", "truck"]
CLASS_TO_ID = {name: idx for idx, name in enumerate(CLASS_NAMES)}
DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[1] / "artifacts" / "nri_composite"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the NRI composite dataset in YOLO format.")
    parser.add_argument("--jcb-root", type=Path, default=Path(r"D:\Nri Dataset\Jcb"))
    parser.add_argument("--tractor-root", type=Path, default=Path(r"D:\Nri Dataset\Tractor Truck"))
    parser.add_argument(
        "--pedestrian-root",
        type=Path,
        default=Path(r"D:\Nri Dataset\Pedestrain\Indian-Pedestrian-Intention-Dataset-main"),
    )
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--pedestrian-stride", type=int, default=15)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-ratio", type=float, default=0.8)
    parser.add_argument("--val-ratio", type=float, default=0.1)
    parser.add_argument("--force", action="store_true", help="Delete any existing prepared dataset before writing.")
    return parser.parse_args()


def ensure_output_dirs(root: Path, force: bool) -> None:
    if root.exists():
        if not force:
            raise FileExistsError(f"{root} already exists. Re-run with --force to replace it.")
        shutil.rmtree(root)

    for split in ("train", "val", "test"):
        (root / "images" / split).mkdir(parents=True, exist_ok=True)
        (root / "labels" / split).mkdir(parents=True, exist_ok=True)


def split_list(items: list, train_ratio: float, val_ratio: float, seed: int) -> dict[str, list]:
    ordered = list(items)
    rng = random.Random(seed)
    rng.shuffle(ordered)

    train_end = int(len(ordered) * train_ratio)
    val_end = train_end + int(len(ordered) * val_ratio)
    return {
        "train": ordered[:train_end],
        "val": ordered[train_end:val_end],
        "test": ordered[val_end:],
    }


def clamp_box(xmin: float, ymin: float, xmax: float, ymax: float, width: float, height: float) -> tuple[float, float, float, float] | None:
    xmin = max(0.0, min(xmin, width))
    xmax = max(0.0, min(xmax, width))
    ymin = max(0.0, min(ymin, height))
    ymax = max(0.0, min(ymax, height))
    if xmax <= xmin or ymax <= ymin:
        return None
    return xmin, ymin, xmax, ymax


def to_yolo_line(class_name: str, xmin: float, ymin: float, xmax: float, ymax: float, width: float, height: float) -> str | None:
    clamped = clamp_box(xmin, ymin, xmax, ymax, width, height)
    if clamped is None:
        return None
    xmin, ymin, xmax, ymax = clamped

    x_center = ((xmin + xmax) / 2.0) / width
    y_center = ((ymin + ymax) / 2.0) / height
    box_width = (xmax - xmin) / width
    box_height = (ymax - ymin) / height
    return f"{CLASS_TO_ID[class_name]} {x_center:.6f} {y_center:.6f} {box_width:.6f} {box_height:.6f}"


def parse_voc_xml(xml_path: Path, label_map: dict[str, str]) -> tuple[str, int, int, list[str]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    filename = root.findtext("filename")
    width = int(float(root.findtext("size/width", "0")))
    height = int(float(root.findtext("size/height", "0")))
    labels: list[str] = []

    for obj in root.findall("object"):
        source_label = (obj.findtext("name") or "").strip().lower()
        target_label = label_map.get(source_label)
        if not target_label:
            continue
        bndbox = obj.find("bndbox")
        if bndbox is None:
            continue
        line = to_yolo_line(
            target_label,
            float(bndbox.findtext("xmin", "0")),
            float(bndbox.findtext("ymin", "0")),
            float(bndbox.findtext("xmax", "0")),
            float(bndbox.findtext("ymax", "0")),
            width,
            height,
        )
        if line:
            labels.append(line)

    return filename, width, height, labels


def collect_jcb_records(root: Path) -> list[dict]:
    annotation_dir = root / "Annotations" / "Annotations"
    records: list[dict] = []
    for xml_path in sorted(annotation_dir.glob("*.xml")):
        filename, _, _, labels = parse_voc_xml(xml_path, {"excavator": "jcb"})
        image_path = root / filename
        if image_path.exists() and labels:
            records.append(
                {
                    "key": image_path.stem,
                    "image_path": image_path,
                    "labels": labels,
                    "source": "jcb",
                }
            )
    return records


def collect_tractor_records(root: Path) -> list[dict]:
    annotation_dir = root / "Annotations" / "Annotations"
    image_lookup = {path.name: path for path in root.rglob("*.jpg")}
    records: list[dict] = []

    for xml_path in sorted(annotation_dir.rglob("*.xml")):
        filename, _, _, labels = parse_voc_xml(xml_path, {"tractor": "tractor", "truck": "truck"})
        image_path = image_lookup.get(filename)
        if image_path and labels:
            records.append(
                {
                    "key": image_path.stem,
                    "image_path": image_path,
                    "labels": labels,
                    "source": "tractor_truck",
                }
            )
    return records


def parse_cvat_boxes(xml_path: Path) -> dict[int, list[tuple[float, float, float, float]]]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    by_frame: dict[int, list[tuple[float, float, float, float]]] = defaultdict(list)
    width = int(root.findtext(".//original_size/width", "1920"))
    height = int(root.findtext(".//original_size/height", "1080"))

    for track in root.findall("track"):
        if (track.attrib.get("label") or "").lower() != "person":
            continue
        for box in track.findall("box"):
            if box.attrib.get("outside") == "1":
                continue
            line = to_yolo_line(
                "person",
                float(box.attrib.get("xtl", "0")),
                float(box.attrib.get("ytl", "0")),
                float(box.attrib.get("xbr", "0")),
                float(box.attrib.get("ybr", "0")),
                width,
                height,
            )
            if line:
                by_frame[int(box.attrib["frame"])].append(line)
    return by_frame


def write_label_file(label_path: Path, labels: list[str]) -> None:
    label_path.write_text("\n".join(labels) + "\n", encoding="utf-8")


def write_image_record(record: dict, split: str, output_root: Path, counter: Counter) -> None:
    image_out = output_root / "images" / split / f"{record['source']}_{record['key']}.jpg"
    label_out = output_root / "labels" / split / f"{record['source']}_{record['key']}.txt"
    shutil.copy2(record["image_path"], image_out)
    write_label_file(label_out, record["labels"])
    counter[split] += 1


def extract_pedestrian_frames(
    pedestrian_root: Path,
    output_root: Path,
    stride: int,
    seed: int,
    train_ratio: float,
    val_ratio: float,
) -> Counter:
    annotation_dir = pedestrian_root / "ipid" / "annotations"
    clips_dir = pedestrian_root / "ipid" / "clips"
    clip_names = sorted(path.stem for path in annotation_dir.glob("*.xml"))
    split_map: dict[str, str] = {}
    for split, names in split_list(clip_names, train_ratio, val_ratio, seed).items():
        for name in names:
            split_map[name] = split

    counter: Counter = Counter()
    for clip_name in clip_names:
        xml_path = annotation_dir / f"{clip_name}.xml"
        video_path = clips_dir / f"{clip_name}.mp4"
        if not video_path.exists():
            continue

        frame_labels = parse_cvat_boxes(xml_path)
        target_frames = sorted(frame for frame, labels in frame_labels.items() if labels and frame % stride == 0)
        if not target_frames:
            continue

        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            continue

        frame_targets = set(target_frames)
        current_frame = 0
        split = split_map[clip_name]
        while frame_targets:
            ok, frame = capture.read()
            if not ok:
                break
            if current_frame in frame_targets:
                image_name = f"pedestrian_{clip_name}_{current_frame:06d}"
                image_out = output_root / "images" / split / f"{image_name}.jpg"
                label_out = output_root / "labels" / split / f"{image_name}.txt"
                cv2.imwrite(str(image_out), frame)
                write_label_file(label_out, frame_labels[current_frame])
                counter[split] += 1
                frame_targets.remove(current_frame)
            current_frame += 1

        capture.release()
    return counter


def write_dataset_yaml(output_root: Path) -> Path:
    dataset_yaml = output_root / "dataset.yaml"
    lines = [
        f"path: {output_root.as_posix()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "names:",
    ]
    for idx, name in enumerate(CLASS_NAMES):
        lines.append(f"  {idx}: {name}")
    dataset_yaml.write_text("\n".join(lines) + "\n", encoding="utf-8")

    classes_txt = output_root / "classes.txt"
    classes_txt.write_text("\n".join(CLASS_NAMES) + "\n", encoding="utf-8")
    return dataset_yaml


def prepare_dataset(
    jcb_root: Path,
    tractor_root: Path,
    pedestrian_root: Path,
    output_root: Path,
    pedestrian_stride: int,
    seed: int,
    train_ratio: float,
    val_ratio: float,
    force: bool,
) -> tuple[Path, dict]:
    ensure_output_dirs(output_root, force=force)

    jcb_records = collect_jcb_records(jcb_root)
    tractor_records = collect_tractor_records(tractor_root)

    image_counter: Counter = Counter()
    for records in (jcb_records, tractor_records):
        for split, items in split_list(records, train_ratio, val_ratio, seed).items():
            for record in items:
                write_image_record(record, split, output_root, image_counter)

    pedestrian_counter = extract_pedestrian_frames(
        pedestrian_root=pedestrian_root,
        output_root=output_root,
        stride=pedestrian_stride,
        seed=seed,
        train_ratio=train_ratio,
        val_ratio=val_ratio,
    )
    image_counter.update(pedestrian_counter)

    dataset_yaml = write_dataset_yaml(output_root)
    summary = {
        "classes": CLASS_NAMES,
        "image_counts": dict(image_counter),
        "sources": {
            "jcb": len(jcb_records),
            "tractor_truck": len(tractor_records),
            "pedestrian_stride": pedestrian_stride,
        },
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return dataset_yaml, summary


def main() -> None:
    args = parse_args()
    dataset_yaml, summary = prepare_dataset(
        jcb_root=args.jcb_root,
        tractor_root=args.tractor_root,
        pedestrian_root=args.pedestrian_root,
        output_root=args.output_root,
        pedestrian_stride=args.pedestrian_stride,
        seed=args.seed,
        train_ratio=args.train_ratio,
        val_ratio=args.val_ratio,
        force=args.force,
    )
    print(f"Prepared dataset at: {dataset_yaml}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
