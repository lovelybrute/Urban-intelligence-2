"""
Urban Intelligence Platform - Edge Multi-Camera Stream Manager

Handles video ingestion across multi-camera bus configurations:
- Front Camera (road surface, traffic flow, forward pedestrians, signs)
- Rear Camera (following traffic, tailgating, rear overtaking)
- Left / Right Lateral Cameras (bus stops, curbside hazards, dividers, lane adherence)
- Interior / Passenger Camera (crowd density, emergency onboard situations)

Supports RTSP streams, pre-recorded video files, live webcams, or synthetic procedural frames.
"""
import time
from typing import Dict, Optional, Any, Generator, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class CameraConfig:
    camera_id: str
    position: str  # front, rear, left, right, interior
    source_type: str  # synthetic, file, rtsp, webcam
    uri: Optional[str] = None  # RTSP URL, file path, or webcam device index
    target_fps: int = 15
    resolution: Tuple[int, int] = (1280, 720)


class MultiCameraManager:
    """
    Coordinates simultaneous ingestion from all onboard bus cameras.
    """

    def __init__(self, bus_id: str):
        self.bus_id = bus_id
        self.cameras: Dict[str, CameraConfig] = {}
        self.captures: Dict[str, Any] = {}
        self._setup_default_bus_rig()

    def _setup_default_bus_rig(self):
        """Sets up standard 4-camera edge sensing configuration."""
        rig = [
            CameraConfig(f"{self.bus_id}_CAM_FRONT", "front", "synthetic", target_fps=20),
            CameraConfig(f"{self.bus_id}_CAM_REAR", "rear", "synthetic", target_fps=15),
            CameraConfig(f"{self.bus_id}_CAM_LEFT", "left", "synthetic", target_fps=15),
            CameraConfig(f"{self.bus_id}_CAM_RIGHT", "right", "synthetic", target_fps=15),
        ]
        for cam in rig:
            self.cameras[cam.camera_id] = cam

    def add_custom_camera(self, config: CameraConfig):
        """Register a custom stream (RTSP, webcam, or video file)."""
        self.cameras[config.camera_id] = config
        if config.source_type in ["file", "rtsp", "webcam"]:
            try:
                import cv2
                src = int(config.uri) if config.source_type == "webcam" else config.uri
                cap = cv2.VideoCapture(src)
                if cap.isOpened():
                    self.captures[config.camera_id] = cap
                    logger.info(f"Connected video stream for {config.camera_id} ({config.source_type})")
            except Exception as ex:
                logger.warning(f"Could not open stream {config.uri}: {ex}")

    def read_frame(self, camera_id: str) -> Tuple[bool, Optional[Any]]:
        """
        Reads next frame from designated camera.
        Returns (success: bool, frame_numpy_array)
        """
        if camera_id not in self.cameras:
            return False, None

        cfg = self.cameras[camera_id]

        # Real video stream
        if camera_id in self.captures:
            cap = self.captures[camera_id]
            ret, frame = cap.read()
            if ret:
                return True, frame
            else:
                # If looped video file, rewind
                if cfg.source_type == "file":
                    cap.set(1, 0)
                    ret, frame = cap.read()
                    return ret, frame
                return False, None

        if cfg.source_type == "synthetic":
            frame = self._generate_synthetic_frame(cfg)
            return frame is not None, frame
        return False, None

    def _generate_synthetic_frame(self, cfg: CameraConfig) -> Any:
        """
        Procedural frame generation for simulation / testing when video hardware is absent.
        Returns a valid RGB / BGR numpy image.
        """
        try:
            import numpy as np
            w, h = cfg.resolution
            # Create tarmac-colored road base (dark gray)
            frame = np.full((h, w, 3), 45, dtype=np.uint8)
            # Add synthetic lane lines
            frame[int(h*0.4):, int(w*0.48):int(w*0.52)] = [220, 220, 220]
            return frame
        except Exception:
            return None

    def get_fleet_telemetry(self) -> Dict[str, Any]:
        """Provides status of all connected cameras for system health MLOps monitoring."""
        status = {}
        for cam_id, cfg in self.cameras.items():
            status[cam_id] = {
                "position": cfg.position,
                "source": cfg.source_type,
                "target_fps": cfg.target_fps,
                "online": cfg.source_type == "synthetic" or (cam_id in self.captures and self.captures[cam_id].isOpened()),
                "is_simulated": cfg.source_type == "synthetic"
            }
        return status
