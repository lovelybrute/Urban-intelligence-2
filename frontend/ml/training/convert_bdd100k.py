"""Convert BDD100K detection JSON into the project's YOLO traffic taxonomy."""
from __future__ import annotations
import argparse,json,shutil
from pathlib import Path
# Must match frontend/ml/configs/yolo_traffic.yaml exactly.\n# BDD100K has no native auto-rickshaw/emergency classes; those require reviewed custom data.\nMAP={"car":0,"bus":1,"truck":2,"motorcycle":3,"bike":5,"bicycle":5,"person":7}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("labels",type=Path);ap.add_argument("images",type=Path)
    ap.add_argument("--output",type=Path,required=True);ap.add_argument("--split",choices=["train","val","test"],default="train");a=ap.parse_args()
    oi=a.output/"images"/a.split;ol=a.output/"labels"/a.split;oi.mkdir(parents=True,exist_ok=True);ol.mkdir(parents=True,exist_ok=True)
    data=json.loads(a.labels.read_text(encoding="utf-8")); n=boxes=0
    for item in data:
        src=a.images/item["name"]
        if not src.is_file(): continue
        from PIL import Image
        with Image.open(src) as im:w,h=im.size
        rows=[]
        for lab in item.get("labels",[]):
            cls=MAP.get(lab.get("category")); box=lab.get("box2d")
            if cls is None or not box: continue
            x1,y1,x2,y2=[float(box[k]) for k in ("x1","y1","x2","y2")]
            rows.append(f"{cls} {((x1+x2)/2)/w:.6f} {((y1+y2)/2)/h:.6f} {(x2-x1)/w:.6f} {(y2-y1)/h:.6f}");boxes+=1
        shutil.copy2(src,oi/src.name);(ol/(src.stem+".txt")).write_text("\n".join(rows)+("\n" if rows else ""),encoding="utf-8");n+=1
    print(f"BDD100K: {n} images, {boxes} traffic/person boxes")
if __name__=="__main__":main()
