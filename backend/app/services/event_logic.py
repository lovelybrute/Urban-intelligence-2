"""Temporal event confirmation helpers.

These rules consume calibrated track observations. They separate candidates
from confirmed events so proximity alone is never reported as an accident.
"""
from math import hypot

def _speed(a,b,fps,pixels_per_meter):
    frames=max(1,b[0]-a[0])
    meters=hypot(b[1]-a[1],b[2]-a[2])/pixels_per_meter
    return meters/(frames/fps)*3.6

def evaluate_vehicle_track(points, fps: float, pixels_per_meter: float, speed_limit_kmh: float):
    if len(points)<3 or fps<=0 or pixels_per_meter<=0:
        return {"rash_driving":False,"reason":"insufficient calibrated observations"}
    speeds=[_speed(a,b,fps,pixels_per_meter) for a,b in zip(points,points[1:])]
    peak=max(speeds,default=0)
    return {"rash_driving":peak>speed_limit_kmh*1.15,
            "peak_speed_kmh":round(peak,1),
            "speed_limit_kmh":speed_limit_kmh,
            "method":"calibrated trajectory speed"}

def evaluate_collision(vehicle_a, vehicle_b, fps: float, pixels_per_meter: float):
    amap={p[0]:p for p in vehicle_a}; bmap={p[0]:p for p in vehicle_b}
    common=sorted(set(amap)&set(bmap))
    if len(common)<3 or pixels_per_meter<=0:
        return {"collision_confirmed":False,"reason":"insufficient calibrated overlap"}
    distances=[hypot(amap[n][1]-bmap[n][1],amap[n][2]-bmap[n][2])/pixels_per_meter for n in common]
    closest=min(distances)
    # This remains evidence screening: visual overlap alone cannot establish physical impact.
    return {"collision_confirmed":False,"closest_distance_m":round(closest,2),
            "collision_candidate":closest<1.5,
            "reason":"candidate requires impact/deceleration evidence or human confirmation"}

def hit_and_run_candidate(collision_candidate: bool, offending_track_visible_after: bool, counterpart_stops: bool):
    candidate=bool(collision_candidate and offending_track_visible_after and counterpart_stops)
    return {"hit_and_run_candidate":candidate,
            "confirmed":False,
            "reason":"candidate requires incident review and ANPR/trajectory evidence" if candidate else "criteria not met"}
