#!/usr/bin/env python3
"""Read-only source inventory + local catalog report for Studio reference batch 01.

Writes reports ONLY inside <workspace>/reference-batches/<batch_id>.
Never unpacks files, imports into Godot, installs programs, or downloads binaries.
Optional --online fetches Poly Haven metadata for curated candidate slugs.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import struct
from pathlib import Path
import urllib.error
import urllib.request
import zipfile

def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def animation_names_from_glb(blob):
    """Read the JSON chunk of glTF 2.0 GLB without extracting scene geometry."""
    if len(blob) < 20:
        raise ValueError("GLB too short")
    magic, version, length = struct.unpack_from("<4sII", blob)
    if magic != b"glTF" or version != 2 or length != len(blob):
        raise ValueError("Invalid glTF 2.0 GLB header")
    offset = 12
    while offset + 8 <= len(blob):
        chunk_length, chunk_type = struct.unpack_from("<II", blob, offset)
        offset += 8
        if offset + chunk_length > len(blob):
            raise ValueError("Invalid GLB chunk length")
        if chunk_type == 0x4E4F534A:  # JSON
            data = json.loads(blob[offset:offset + chunk_length].rstrip(b"\x00 \t\r\n"))
            return [a.get("name") or "(unnamed)" for a in data.get("animations", [])]
        offset += chunk_length
    raise ValueError("No JSON chunk in GLB")

def inventory_zip(path):
    with zipfile.ZipFile(path) as z:
        members=z.infolist()
        counts=collections.Counter(Path(f.filename).suffix.lower() for f in members if not f.is_dir())
        anims=[]
        errors=[]
        inspected=[]
        for f in members:
            suffix=Path(f.filename).suffix.lower()
            if f.is_dir() or suffix not in (".gltf", ".glb"):
                continue
            if f.file_size > 64*1024*1024:
                errors.append({"archive_member":f.filename, "error":"skipped above 64 MiB metadata parsing limit"})
                continue
            inspected.append(f.filename)
            try:
                blob=z.read(f)
                if suffix==".glb":
                    names=animation_names_from_glb(blob)
                else:
                    data=json.loads(blob)
                    names=[a.get("name") or "(unnamed)" for a in data.get("animations", [])]
                anims.extend({"archive_member":f.filename,"name":name} for name in names)
            except (ValueError,UnicodeError,OSError,RuntimeError,struct.error) as exc:
                errors.append({"archive_member":f.filename,"error":str(exc)})
        likely=[f.filename for f in members if any(k in f.filename.lower() for k in ("walk","zombie","idle","reach","shuffle","limp"))]
        return {"member_count":len(members),"extensions":dict(sorted(counts.items())),
                "sample_filenames":[f.filename for f in members[:40]],"filename_matches":likely[:100],
                "gltf_animations":anims[:1000], "gltf_animation_count_found":len(anims),
                "gltf_scene_files_scanned":inspected, "gltf_parse_errors":errors,
                "note":"Only glTF JSON and GLB animation names inspected. FBX and Blender actions require Blender/FBX inspection."}

def api_json(url):
    req=urllib.request.Request(url, headers={"User-Agent":"OptiPlexStudio-reference-intake/0.1 (+https://github.com/SteezyMode/OptiplexStudio)","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=12) as r:
        return json.load(r)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--workspace",type=Path,default=Path("~/StudioProjects/.studio/art-director").expanduser())
    ap.add_argument("--catalog",type=Path,default=Path(__file__).resolve().parent.parent/"catalogs/threshold-reference-batch-01.json")
    ap.add_argument("--online",action="store_true",help="Fetch Poly Haven metadata only; no asset binaries")
    args=ap.parse_args()
    manifest=json.loads(args.catalog.read_text(encoding="utf-8"))
    workspace=args.workspace.expanduser().resolve()
    if not workspace.is_dir():
        ap.error("Workspace does not exist: "+str(workspace))
    out=workspace/"reference-batches"/manifest["batch_id"]
    out.mkdir(parents=True,exist_ok=True)
    records=[]
    for item in manifest["entries"]:
        row=dict(item)
        row["local_status"]="not_checked"
        if "local_file" in item:
            local=(workspace/item["local_file"]).resolve()
            if not local.is_relative_to(workspace):
                row["local_status"]="unsafe_path"
            elif not local.is_file():
                row["local_status"]="missing"
            else:
                row["bytes"]=local.stat().st_size
                row["sha256"]=sha256(local)
                expected=item.get("expected_sha256")
                row["local_status"]="verified" if expected and row["sha256"]==expected else ("checksum_mismatch" if expected else "present_unverified")
                if local.suffix.lower()==".zip":
                    try: row["archive"]=inventory_zip(local)
                    except (zipfile.BadZipFile,OSError,RuntimeError) as e:
                        row["archive_error"]=str(e)
        if args.online and "polyhaven_id" in item:
            asset_id=item["polyhaven_id"]
            try:
                meta=api_json("https://api.polyhaven.com/info/"+asset_id)
                files=api_json("https://api.polyhaven.com/files/"+asset_id)
                row["polyhaven"]={"name":meta.get("name"),"type":meta.get("type"),
                                  "category":meta.get("category"),"tags":meta.get("tags",[]),
                                  "authors":meta.get("authors",{}),
                                  "files_top_level_keys":list(files)[:20],
                                  "files_tree":files}
            except (urllib.error.URLError,ValueError,TimeoutError,OSError) as e:
                row["polyhaven_error"]=str(e)
        records.append(row)
    obj={"batch":manifest["batch_id"],"scanned_at":dt.datetime.now(dt.timezone.utc).isoformat(),
         "workspace":str(workspace),"online":args.online,"entries":records}
    target=out/"source-inventory.json"
    target.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    lines=["# Source intake — "+manifest["batch_id"],"",
           "Scanned: "+obj["scanned_at"],"",
           "Note: Candidate does not mean imported, approved for final game art, or animation compatible.",""]
    for r in records:
        lines.extend(["## "+r["title"],"","- Category: "+r["category"],
                      "- Source: "+r["source_url"],
                      "- License claimed on source: "+r["license"],
                      "- Candidate status: "+r["status"],
                      "- Local state: "+r["local_status"]])
        if "sha256" in r:lines.append("- SHA256: "+r["sha256"])
        if "archive" in r:
            a=r["archive"]
            lines.append("- ZIP members: "+str(a["member_count"]))
            lines.append("- Extensions: "+json.dumps(a["extensions"]))
            lines.append("- Embedded glTF/GLB animation names found: "+str(a["gltf_animation_count_found"]))\n            lines.append("- glTF/GLB files inspected: "+str(len(a.get("gltf_scene_files_scanned", []))))\n            lines.append("- Other animation actions: FBX and .blend not yet parsed")\n            if a.get("gltf_parse_errors"):lines.append("- Parser warnings: "+json.dumps(a["gltf_parse_errors"][:4]))
            matches=(a["filename_matches"][:16]+[x.get("name","") for x in a["gltf_animations"][:16]])
            lines.append("- Likely motion names: "+", ".join(x for x in matches if x) if matches else "- Motions: further FBX/Blender parsing needed")
        if "polyhaven" in r:lines.append("- Poly Haven metadata fetched: yes")
        if "polyhaven_error" in r:lines.append("- Poly Haven API warning: "+r["polyhaven_error"])
        lines.extend(["- Notes: "+r.get("notes",""),""])
    (out/"INVENTORY.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("Scanned",len(records),"sources; archive details and candidate metadata saved in",out)
    print("No binaries downloaded, extracted, installed or added to Godot.")
if __name__=="__main__":
    main()
