"""Video tracking and temporal safety analytics.

Uses Ultralytics track() with ByteTrack. Event labels are rule-derived from
measured tracks and are not presented as separately trained neural models.
"""
from collections import defaultdict
from math import hypot
from pathlib import Path
import tempfile
import os

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

VEHICLES={"car","motorcycle","bus","truck","bicycle","auto_rickshaw","emergency"}
REPO_ROOT=Path(__file__).resolve().parents[3]
BACKEND_WEIGHTS=Path(__file__).resolve().parents[2]/"ml"/"weights"
REPO_WEIGHTS=REPO_ROOT/"frontend"/"ml"/"weights"

def _weight(name: str) -> Path:
    local=BACKEND_WEIGHTS/name
    repo=REPO_WEIGHTS/name
    return local if local.exists() else repo
_model=None

def _model_instance():
    global _model
    if YOLO is None:
        raise RuntimeError("Ultralytics is not installed")
    if _model is None:
        custom=_weight("traffic_india.pt")
        local=_weight("traffic_coco.pt")
        source=str(custom if custom.exists() else local) if (custom.exists() or local.exists()) else "yolo11n.pt"
        _model=YOLO(source)
    return _model

def analyse_video(raw: bytes, confidence: float=.25):
    if not raw:
        raise ValueError("Empty video")
    tracks=defaultdict(list)
    class_by_track={}
    pedestrian_frames=defaultdict(int)
    vehicle_frames=defaultdict(int)
    frame_no=0
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(raw); path=f.name
    try:
        results=_model_instance().track(source=path, tracker="bytetrack.yaml", conf=confidence, persist=True, stream=True, verbose=False, imgsz=int(os.getenv("VIDEO_AI_IMGSZ","320")), device="cpu", vid_stride=max(1,int(os.getenv("VIDEO_AI_STRIDE","2"))))
        for result in results:
            frame_no+=1
            if result.boxes is None or result.boxes.id is None: continue
            for box in result.boxes:
                tid=int(box.id[0].item()); cid=int(box.cls[0].item()); name=str(result.names[cid])
                if name not in VEHICLES and name!="person": continue
                x1,y1,x2,y2=[float(v) for v in box.xyxy[0].tolist()]
                cx,cy=(x1+x2)/2,(y1+y2)/2
                tracks[tid].append((frame_no,cx,cy))
                class_by_track[tid]=name
                if name=="person": pedestrian_frames[tid]+=1
                else: vehicle_frames[tid]+=1
    finally:
        Path(path).unlink(missing_ok=True)

    motion=[]
    rash_candidates=[]
    pedestrian_risk_candidates=[]
    accident_candidates=[]
    for tid, pts in tracks.items():
        if len(pts)<3: continue
        distance=sum(hypot(b[1]-a[1],b[2]-a[2]) for a,b in zip(pts,pts[1:]))
        steps=max(1,pts[-1][0]-pts[0][0])
        px_per_frame=distance/steps
        item={"track_id":tid,"class_name":class_by_track[tid],"frames":len(pts),"motion_px_per_frame":round(px_per_frame,2)}
        motion.append(item)
        # Candidate only: pixel motion cannot establish legal road speed without calibration.
        if class_by_track[tid] in VEHICLES and px_per_frame>35:
            rash_candidates.append({**item,"reason":"high image-plane motion; requires calibrated speed/trajectory validation"})

    # Pairwise trajectory proximity is a screening signal, not accident proof.
    ids=list(tracks)
    for i, aid in enumerate(ids):
        for bid in ids[i+1:]:
            if class_by_track.get(aid) not in VEHICLES and class_by_track.get(bid) not in VEHICLES:
                continue
            amap={p[0]:p for p in tracks[aid]}
            bmap={p[0]:p for p in tracks[bid]}
            common=set(amap).intersection(bmap)
            if not common: continue
            closest=min(hypot(amap[n][1]-bmap[n][1],amap[n][2]-bmap[n][2]) for n in common)
            acls,bcls=class_by_track.get(aid),class_by_track.get(bid)
            if {acls,bcls} & {"person"} and ({acls,bcls} & VEHICLES) and closest < 80:
                pedestrian_risk_candidates.append({"track_ids":[aid,bid],"min_pixel_distance":round(closest,2),
                    "reason":"vehicle-person tracks entered close image-plane proximity"})
            if acls in VEHICLES and bcls in VEHICLES and closest < 45:
                accident_candidates.append({"track_ids":[aid,bid],"min_pixel_distance":round(closest,2),
                    "reason":"vehicle tracks entered collision-proximity; requires impact/deceleration confirmation"})

    return {
        "engine":"YOLO + ByteTrack",
        "frames_processed":frame_no,
        "unique_tracks":len(tracks),
        "vehicle_tracks":sum(1 for x in class_by_track.values() if x in VEHICLES),
        "pedestrian_tracks":sum(1 for x in class_by_track.values() if x=="person"),
        "tracks":motion,
        "rash_driving_candidates":rash_candidates,
        "pedestrian_risk_candidates":pedestrian_risk_candidates,
        "accident_candidates":accident_candidates,
        "hit_and_run_candidates":[],
        "accident_events":[],
        "limitations":[
            "Rash-driving output is candidate screening, not a legal speed determination.",
            "Hit-and-run and accident confirmation require collision/trajectory evidence and scene calibration.",
            "Pedestrian vulnerability requires road-zone geometry and vehicle trajectory context."
        ]
    }
