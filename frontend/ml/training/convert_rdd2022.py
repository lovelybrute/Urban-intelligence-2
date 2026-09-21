"""Convert extracted RDD2022 Pascal-VOC annotations to the project's YOLO road taxonomy."""
from __future__ import annotations
import argparse, shutil, xml.etree.ElementTree as ET
from pathlib import Path

MAP={"D00":0,"D10":1,"D20":2,"D40":4}
EXT={".jpg",".jpeg",".png",".webp"}

def convert(xml:Path, out:Path):
    root=ET.parse(xml).getroot()
    size=root.find("size"); w=float(size.findtext("width")); h=float(size.findtext("height"))
    rows=[]
    for obj in root.findall("object"):
        name=obj.findtext("name","").strip()
        if name not in MAP: continue
        b=obj.find("bndbox")
        xmin,ymin,xmax,ymax=[float(b.findtext(k)) for k in ("xmin","ymin","xmax","ymax")]
        x=((xmin+xmax)/2)/w; y=((ymin+ymax)/2)/h
        bw=(xmax-xmin)/w; bh=(ymax-ymin)/h
        rows.append(f"{MAP[name]} {x:.6f} {y:.6f} {bw:.6f} {bh:.6f}")
    out.write_text("\n".join(rows)+("\n" if rows else ""),encoding="utf-8")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("source",type=Path); ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--split",choices=["train","val","test"],default="train"); a=ap.parse_args()
    images=a.output/"images"/a.split; labels=a.output/"labels"/a.split
    images.mkdir(parents=True,exist_ok=True); labels.mkdir(parents=True,exist_ok=True)
    xmls=list(a.source.rglob("*.xml")); converted=0
    for xml in xmls:
        stem=xml.stem
        img=next((p for p in xml.parent.parent.rglob(stem+".*") if p.suffix.lower() in EXT),None)
        if img is None: continue
        shutil.copy2(img,images/img.name); convert(xml,labels/(img.stem+".txt")); converted+=1
    print(f"RDD2022: converted {converted}/{len(xmls)} annotations into {a.output}")
if __name__=="__main__": main()
