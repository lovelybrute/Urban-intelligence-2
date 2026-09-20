# Machine Learning Subsystem - Mobile Urban Intelligence Platform

This directory contains the computer vision datasets, training pipelines, inference modules, and evaluation scripts for edge onboard public bus processing.

---

## 1. Models Overview

| Model | Architecture | Dataset Benchmark | Target Classes | Target Device |
|-------|--------------|-------------------|----------------|---------------|
| **Road Defect Detector** | YOLOv8s | Road Damage Dataset (RDD2022) | Potholes, Cracks, Waterlogging, Damaged Dividers, Missing Signs | Jetson Orin / x86 Edge |
| **Traffic & Vehicle Tracker** | YOLOv8n + ByteTrack | Indian Driving Dataset (IDD) + COCO | Car, Bus, Truck, Motorcycle, Auto-Rickshaw, Bicycle, Emergency | Jetson Nano / Orin |
| **ANPR / Plate OCR** | YOLOv8n + Bilateral Filter OCR | Indian Motor Vehicle Plates Dataset | License Plate BBox + OCR Characters | Bus Edge Compute |

---

## 2. Directory Structure

```
ml/
├── configs/
│   ├── yolo_road_defect.yaml   # Dataset split & classes for road surface defects
│   ├── yolo_traffic.yaml       # Vehicle classes tailored for Indian traffic
│   └── anpr_plate.yaml         # License plate localization setup
├── training/
│   ├── train_defect_detector.py  # Defect model training pipeline
│   └── train_traffic_detector.py # Vehicle classification training
├── evaluation/
│   └── evaluate_models.py        # mAP50, Precision, Recall, F1 score evaluator
├── inference/                  # Batch & video stream inference scripts
├── datasets/                   # Symlinks or local dataset directory
└── artifacts/                  # Exported PyTorch/ONNX checkpoints
```

---

## 3. Dataset Setup

1. **Road Defect Dataset**: Download the [RDD2022](https://github.com/sekilab/RoadDamageDetector) (India subset) and extract into `ml/datasets/road_defects/`.
2. **Traffic Dataset**: Download the [Indian Driving Dataset](http://idd.insaan.iiit.ac.in/) or filtered COCO vehicles and extract into `ml/datasets/traffic/`.

---

## 4. Reproducible Training Commands

### Recommended hybrid setup (Windows / RTX 2050)

From the repository root:

```powershell
.\setup-hybrid-ai.ps1
```

This verifies the trained 50-epoch road model, downloads the official
Ultralytics COCO checkpoint for traffic/person tracking, checks the OCR engine,
and writes `frontend/ml/model_manifest.json`. Pretrained weights are labelled as
pretrained; they are not reported as custom training.

Optional custom training becomes available after YOLO-format datasets are placed
under `frontend/ml/datasets/traffic`, `license_plates`, and `infrastructure`:

```powershell
.\setup-hybrid-ai.ps1 -TrainCustom
```

The custom command uses `batch=4`, `imgsz=640`, and `workers=2` to fit a 4 GB
RTX 2050. It refuses to train when images, labels, validation data, or CUDA are
missing.

### Individual training commands

To train the Road Defect model on an NVIDIA GPU workstation from the repository root:
```bash
python frontend/ml/training/train_defect_detector.py --epochs 50 --batch 16 --imgsz 640
```

To train the Traffic Vehicle classifier:
```bash
python frontend/ml/training/train_traffic_detector.py --epochs 60 --batch 16 --imgsz 640
```

---

## 5. Model Evaluation

Evaluate accuracy on held-out validation test sets:
```bash
python frontend/ml/evaluation/evaluate_models.py --weights frontend/ml/weights/road_defect_best.pt --data frontend/ml/configs/yolo_road_defect.yaml
```

> **Note on Evaluation Ethics**:
> The platform adheres to strict engineering honesty. If a local model weight is not yet trained, the system reports `MODEL NOT TRAINED` and falls back to deterministic OpenCV edge heuristics rather than fabricating fake precision numbers.
