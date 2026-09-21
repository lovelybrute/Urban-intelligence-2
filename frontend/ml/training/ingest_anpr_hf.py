"""Ingest keremberke/license-plate-object-detection from HuggingFace cache into YOLO format.

Converts COCO format annotations into YOLOv8 format:
- Remaps license plate class to 0
- Normalizes bboxes to [x_center, y_center, width, height]
- Clamps any slight rounding overflow to [0.0, 1.0]
- Validates the resulting dataset using validate_yolo_dataset.py
"""
from __future__ import annotations

import json
import shutil
import sys
import zipfile
from pathlib import Path
from huggingface_hub import hf_hub_download

REPO_ROOT = Path(__file__).resolve().parents[3]
ML_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ML_ROOT / "datasets" / "license_plates"
EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def process_zip(zip_path: Path, split_name: str, max_samples: int | None = None):
    print(f"\nProcessing {zip_path.name} -> split: {split_name}...")
    dst_img_dir = DATASET_DIR / "images" / split_name
    dst_lab_dir = DATASET_DIR / "labels" / split_name
    dst_img_dir.mkdir(parents=True, exist_ok=True)
    dst_lab_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as z:
        # Load coco annotations
        if "_annotations.coco.json" not in z.namelist():
            raise FileNotFoundError(f"Missing _annotations.coco.json in {zip_path}")
        coco_data = json.loads(z.read("_annotations.coco.json"))

        images_by_id = {img["id"]: img for img in coco_data.get("images", [])}
        annotations_by_img = {}
        for ann in coco_data.get("annotations", []):
            img_id = ann["image_id"]
            annotations_by_img.setdefault(img_id, []).append(ann)

        img_ids = list(images_by_id.keys())
        if max_samples and max_samples < len(img_ids):
            img_ids = img_ids[:max_samples]

        extracted = 0
        boxes_written = 0

        for img_id in img_ids:
            img_info = images_by_id[img_id]
            file_name = img_info["file_name"]
            img_w = float(img_info["width"])
            img_h = float(img_info["height"])

            if file_name not in z.namelist():
                continue

            # Extract image
            target_img_path = dst_img_dir / file_name
            with z.open(file_name) as src_f, open(target_img_path, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)

            # Process labels
            label_stem = Path(file_name).stem
            target_lab_path = dst_lab_dir / f"{label_stem}.txt"

            lines = []
            for ann in annotations_by_img.get(img_id, []):
                bbox = ann.get("bbox", [])
                if len(bbox) != 4:
                    continue
                x_min, y_min, bw, bh = bbox
                if bw <= 0 or bh <= 0 or img_w <= 0 or img_h <= 0:
                    continue

                xc = (x_min + bw / 2.0) / img_w
                yc = (y_min + bh / 2.0) / img_h
                w = bw / img_w
                h = bh / img_h

                # Clamp strictly to [0.0, 1.0]
                xc = max(0.0, min(1.0, xc))
                yc = max(0.0, min(1.0, yc))
                w = max(0.0, min(1.0, w))
                h = max(0.0, min(1.0, h))

                lines.append(f"0 {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")
                boxes_written += 1

            target_lab_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
            extracted += 1

        print(f"Extracted {extracted} images, {boxes_written} boxes to {split_name}")
        return extracted, boxes_written


def main():
    print("=" * 60)
    print("Ingesting Keremberke License Plate Dataset for ANPR")
    print("=" * 60)

    # Clean existing destination files safely
    for split in ["train", "val", "test"]:
        for sub in ["images", "labels"]:
            p = DATASET_DIR / sub / split
            if p.exists():
                for f in p.glob("*"):
                    try:
                        if f.is_file():
                            f.unlink()
                    except Exception:
                        pass
            p.mkdir(parents=True, exist_ok=True)

    # Download train and valid zips
    print("Ensuring dataset zips are downloaded...")
    valid_zip = Path(hf_hub_download("keremberke/license-plate-object-detection", "data/valid.zip", repo_type="dataset"))
    train_zip = Path(hf_hub_download("keremberke/license-plate-object-detection", "data/train.zip", repo_type="dataset"))

    # Ingest validation (1765 images) -> val
    process_zip(valid_zip, "val")

    # Ingest train (6176 images) -> train
    process_zip(train_zip, "train")

    print("\nDataset ingestion complete. Validating with validate_yolo_dataset.py...")
    import subprocess
    validator = Path(__file__).with_name("validate_yolo_dataset.py")
    res = subprocess.run([sys.executable, str(validator), str(DATASET_DIR), "--classes", "1"], capture_output=True, text=True)
    print("Validation Output:\n", res.stdout)
    if res.returncode != 0:
        print("Validation FAILED:\n", res.stderr)
        sys.exit(res.returncode)
    print("Dataset validation PASSED successfully!")


if __name__ == "__main__":
    main()
