from io import BytesIO

from PIL import Image

from app.services import road_detector


class _Scalar:
    def __init__(self, value):
        self.value = value

    def item(self):
        return self.value


class _Coordinates:
    def __init__(self, values):
        self.values = values

    def tolist(self):
        return self.values


class _Box:
    cls = [_Scalar(0)]
    conf = [_Scalar(0.875)]
    xyxy = [_Coordinates([32, 64, 160, 256])]


class _Result:
    boxes = [_Box()]
    names = {0: "pothole"}


class _CandidateBox:
    cls = [_Scalar(0)]
    conf = [_Scalar(0.91)]
    xyxy = [_Coordinates([44, 42, 210, 216])]


class _CandidateResult:
    boxes = [_CandidateBox()]
    names = {0: "Pothole"}


class _Model:
    def predict(self, **kwargs):
        assert kwargs["source"].shape == (160, 160, 3)
        assert kwargs["imgsz"] == 160
        return [_Result()]


class _CandidateModel:
    def predict(self, **kwargs):
        assert kwargs["source"].shape == (160, 160, 3)
        assert kwargs["imgsz"] == 160
        return [_CandidateResult()]


def test_detection_scales_boxes_back_to_original_image(monkeypatch):
    image = Image.new("RGB", (1280, 1280), color="gray")
    raw = BytesIO()
    image.save(raw, format="JPEG")

    monkeypatch.setattr(road_detector, "get_model", lambda: _Model())
    monkeypatch.setattr(road_detector, "INFERENCE_SIZE", 160)

    detections, timing = road_detector.detect_road_defects(raw.getvalue(), 0.25)

    assert set(timing) >= {
        "preprocess_ms",
        "model_ready_ms",
        "inference_ms",
        "waterlogging_ms",
        "postprocess_ms",
        "total_ms",
    }
    assert timing["total_ms"] >= 0

    assert detections == [
        {
            "class_id": 0,
            "class_name": "pothole",
            "confidence": 0.875,
            "raw_model_confidence": 0.875,
            "detection_method": "CUSTOM YOLO / TRAINED MODEL",
            "bbox": {
                "x1": 256.0,
                "y1": 512.0,
                "x2": 1280.0,
                "y2": 2048.0,
            },
        }
    ]


def test_detection_uses_pretrained_pothole_model_when_available(monkeypatch):
    image = Image.new("RGB", (1280, 1280), color="gray")
    raw = BytesIO()
    image.save(raw, format="JPEG")

    monkeypatch.setattr(road_detector, "get_model", lambda: _Model())
    monkeypatch.setattr(road_detector, "get_pretrained_pothole_model", lambda: _CandidateModel())
    monkeypatch.setattr(road_detector, "USE_PRETRAINED_POTHOLE_MODEL", True)
    monkeypatch.setattr(road_detector, "INFERENCE_SIZE", 160)

    detections, _ = road_detector.detect_road_defects(raw.getvalue(), 0.25)
    potholes = [d for d in detections if d["class_name"] == "pothole"]

    assert len(potholes) >= 1
    assert potholes[0]["confidence"] >= 0.875


def test_model_confidence_is_not_boosted_by_multi_pass_fusion():
    detections = [
        {
            "class_name": "pothole",
            "confidence": 0.18,
            "raw_model_confidence": 0.18,
            "bbox": {"x1": 0, "y1": 0, "x2": 100, "y2": 100},
        },
        {
            "class_name": "pothole",
            "confidence": 0.16,
            "raw_model_confidence": 0.16,
            "bbox": {"x1": 2, "y1": 2, "x2": 98, "y2": 98},
        },
    ]

    fused = road_detector._fuse_same_class_evidence(detections)

    assert len(fused) == 1
    assert fused[0]["confidence"] == 0.18
    assert fused[0]["raw_model_confidence"] == 0.18
    assert fused[0]["evidence_count"] == 2
