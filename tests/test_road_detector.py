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


class _Model:
    def predict(self, **kwargs):
        assert kwargs["source"].shape == (640, 640, 3)
        assert kwargs["imgsz"] == road_detector.INFERENCE_SIZE
        return [_Result()]


def test_detection_scales_boxes_back_to_original_image(monkeypatch):
    image = Image.new("RGB", (1280, 1280), color="gray")
    raw = BytesIO()
    image.save(raw, format="JPEG")

    monkeypatch.setattr(road_detector, "get_model", lambda: _Model())
    monkeypatch.setattr(road_detector, "INFERENCE_SIZE", 320)

    detections = road_detector.detect_road_defects(raw.getvalue(), 0.25)

    assert detections == [
        {
            "class_id": 0,
            "class_name": "pothole",
            "confidence": 0.875,
            "bbox": {
                "x1": 64.0,
                "y1": 128.0,
                "x2": 320.0,
                "y2": 512.0,
            },
        }
    ]
