# Urban Intelligence multi-dataset training plan

## Target pipelines

- **Road detector:** pothole, longitudinal crack, transverse crack, alligator crack, other road damage.
- **Infrastructure detector:** waterlogging, damaged/missing divider, damaged/missing zebra crossing, damaged/missing traffic sign.
- **Traffic detector/tracker:** person, car, motorcycle, bus, truck, bicycle, auto-rickshaw, emergency vehicle.
- **ANPR:** license-plate localization followed by OCR.
- **Traffic density:** derived from tracked vehicle counts/road occupancy; it is not a single object class.
- **Incident tracking:** temporal rules over tracks, speed/direction changes and evidence. Hit-and-run/rash driving must not be represented as a single-frame YOLO label.

## Approved starting sources

1. RDD2022 for road damage.
2. BDD100K for traffic/person/sign detection, tracking and road context.
3. Mapillary Traffic Sign Dataset for additional sign diversity where its license permits the project use.
4. UFPR-ALPR only after the required academic/non-commercial access approval.

Do not scrape arbitrary copyrighted images. Do not commit source datasets or restricted images to Git.

## Important annotation gap

Public datasets do not directly solve every infrastructure requirement. In particular, **missing** divider/zebra/sign is contextual: an image can only be labelled missing when the scene is known to require that infrastructure. Build a reviewed custom SIH set for these classes. Waterlogging and damaged infrastructure likewise need reviewed bounding boxes/segmentation masks.

## Workflow

1. Run `python frontend/ml/training/prepare_multitask_datasets.py`.
2. Download/request approved datasets according to their terms into `frontend/ml/datasets/_raw/`.
3. Convert source annotations into the target YOLO taxonomy.
4. Deduplicate before splitting so near-identical frames cannot leak across train/val/test.
5. Keep a held-out field test set from Indian bus/road footage.
6. Train road/infrastructure/traffic/ANPR independently using `train_custom_models.py`.
7. Evaluate per-class precision, recall, mAP50 and mAP50-95. Do not replace deployed weights solely because training completed.
8. Export accepted checkpoints to ONNX/TensorRT and benchmark warm inference latency on the actual target hardware.
