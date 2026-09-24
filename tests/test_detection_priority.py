from app.api.routes.detection import _prefer_model_over_water_heuristic


def _detection(class_name, method, bbox, confidence=0.8):
    return {
        "class_name": class_name,
        "detection_method": method,
        "confidence": confidence,
        "bbox": bbox,
    }


def test_overlapping_heuristic_waterlogging_is_removed_for_model_pothole():
    pothole = _detection(
        "pothole", "CUSTOM YOLO / TRAINED MODEL", {"x1": 100, "y1": 100, "x2": 220, "y2": 220}
    )
    heuristic_water = _detection(
        "waterlogging", "COMPUTER-VISION PROTOTYPE", {"x1": 80, "y1": 80, "x2": 260, "y2": 260}, 0.65
    )

    filtered = _prefer_model_over_water_heuristic([pothole, heuristic_water])

    assert filtered == [pothole]


def test_model_waterlogging_is_never_removed():
    model_water = _detection(
        "waterlogging", "CUSTOM YOLO / TRAINED MODEL", {"x1": 100, "y1": 100, "x2": 220, "y2": 220}
    )
    filtered = _prefer_model_over_water_heuristic([model_water])
    assert filtered == [model_water]


def test_non_overlapping_heuristic_waterlogging_can_remain():
    pothole = _detection(
        "pothole", "CUSTOM YOLO / TRAINED MODEL", {"x1": 100, "y1": 100, "x2": 180, "y2": 180}
    )
    heuristic_water = _detection(
        "waterlogging", "COMPUTER-VISION PROTOTYPE", {"x1": 400, "y1": 400, "x2": 700, "y2": 550}, 0.65
    )
    filtered = _prefer_model_over_water_heuristic([pothole, heuristic_water])
    assert filtered == [pothole, heuristic_water]
