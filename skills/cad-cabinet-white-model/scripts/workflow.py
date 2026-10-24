#!/usr/bin/env python3
"""One reusable CLI for building, camera proofs, and selected final renders."""
import argparse
import base64
import hashlib
import html
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from project_spec import digest, load


def emit(**payload):
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def file_hash(path):
    result = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b""):
            result.update(chunk)
    return result.hexdigest()


def find_blender(explicit):
    result = explicit or shutil.which("blender")
    if not result and Path("/Applications/Blender.app/Contents/MacOS/Blender").is_file():
        result = "/Applications/Blender.app/Contents/MacOS/Blender"
    if not result:
        raise ValueError("Blender not found; supply --blender /path/to/blender")
    return result


def contact_sheet(manifest, out):
    entries = manifest["renders"]
    cells = []
    for entry in entries:
        image = Path(entry["image"])
        data = base64.b64encode(image.read_bytes()).decode()
        caption = html.escape(f'{entry["id"]} | {entry["height_mm"]:g} mm | {entry["lens_mm"]:g} mm lens')
        cells.append(f'<figure><img src="data:image/png;base64,{data}"><figcaption>{caption}</figcaption></figure>')
    page = '<!doctype html><meta charset="utf-8"><title>Camera proofs</title><style>body{font:16px sans-serif;background:#ececea}main{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}figure{margin:0;background:white;padding:10px}img{width:100%}figcaption{padding-top:8px}</style><main>'+''.join(cells)+'</main>'
    (out/"camera-proofs.html").write_text(page, encoding="utf-8")
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return {"html": str(out/"camera-proofs.html"), "note": "PNG contact sheet needs Pillow; individual images are ready"}
    columns = min(3, len(entries))
    rows = (len(entries)+columns-1)//columns
    sheet = Image.new("RGB", (columns*480, rows*410), "#e8e8e4")
    draw = ImageDraw.Draw(sheet)
    for i, entry in enumerate(entries):
        with Image.open(entry["image"]) as raw:
            image = raw.convert("RGB")
        image.thumbnail((460, 360))
        x, y = i % columns*480, i//columns*410
        sheet.paste(image, (x+(480-image.width)//2, y+10+(360-image.height)//2))
        draw.text((x+12, y+378), f'{entry["id"]} | h={entry["height_mm"]:g}mm | {entry["lens_mm"]:g}mm', fill="#222222")
    sheet.save(out/"camera-proofs.png")
    return {"png": str(out/"camera-proofs.png"), "html": str(out/"camera-proofs.html")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["validate", "build", "preview", "final"])
    parser.add_argument("--project", required=True)
    parser.add_argument("--blend", help="Existing source file; never overwritten")
    parser.add_argument("--out", help="Separate generated-work directory")
    parser.add_argument("--blender")
    parser.add_argument("--cameras", nargs="+", help="IDs; required for final")
    parser.add_argument("--engine", choices=["AUTO", "WORKBENCH", "CYCLES", "BLENDER_EEVEE"], default="AUTO")
    parser.add_argument("--device", choices=["AUTO", "CPU"], default="AUTO")
    parser.add_argument("--size", type=int, help="Longest image edge")
    parser.add_argument("--samples", type=int)
    parser.add_argument("--force", action="store_true", help="Ignore a matching render cache")
    args = parser.parse_args()
    project_path = Path(args.project).resolve()
    project = load(project_path)
    if args.stage == "validate":
        emit(ok=True, components=len(project.get("components", [])), cameras=len(project.get("cameras", [])))
        return
    if not args.out:
        parser.error("--out is required")
    out = Path(args.out).resolve()
    if args.stage == "build" and args.blend:
        parser.error("build starts a new scene; use preview/final for an existing file")
    if args.stage == "build" and project.get("mode", "build") != "build":
        parser.error("mode=existing cannot be used for build")
    source = Path(args.blend).resolve() if args.blend else None
    if args.stage != "build" and (not source or not source.is_file()):
        parser.error("preview/final require --blend pointing to an existing file")
    dest = out/("model.blend" if args.stage == "build" else args.stage+"-scene.blend")
    if source == dest:
        parser.error("Output would overwrite the source .blend; choose a separate --out directory")
    available = {cam["id"] for cam in project.get("cameras", [])}
    if args.stage == "final" and not args.cameras:
        parser.error("final requires explicit --cameras IDs; never render every candidate by default")
    selected = args.cameras or [c["id"] for c in project.get("cameras", [])]
    if args.stage != "build" and (not selected or set(selected)-available):
        parser.error("No cameras selected, or an unknown camera ID was requested")
    size = args.size if args.size is not None else (640 if args.stage == "preview" else 2400)
    samples = args.samples if args.samples is not None else (12 if args.stage == "preview" else 128)
    if size < 64 or samples < 1:
        parser.error("size must be >=64 and samples >=1")
    out.mkdir(parents=True, exist_ok=True)
    scripts = Path(__file__).resolve().parent
    cache_key = digest({"project": project, "source": file_hash(source) if source else None,
                        "stage": args.stage, "cameras": selected, "engine": args.engine,
                        "size": size, "samples": samples, "device": args.device,
                        "worker": file_hash(scripts/"blender_worker.py"), "spec": file_hash(scripts/"project_spec.py")})
    result_file = out/(args.stage+"-result.json")
    if result_file.is_file() and not args.force and args.stage != "build":
        cached = json.loads(result_file.read_text())
        files = [Path(e["image"]) for e in cached.get("renders", [])]+[dest]
        intact = all(p.is_file() and p.stat().st_size for p in files)
        if intact:
            intact = cached.get("scene_sha256") == file_hash(dest) and all(
                entry.get("sha256") == file_hash(entry["image"]) for entry in cached.get("renders", []))
        if cached.get("cache_key") == cache_key and intact:
            emit(ok=True, cached=True, result=str(result_file), proofs=cached.get("proofs"))
            return
    request = {"stage": args.stage, "project": project, "out": str(out), "destination": str(dest),
               "selected": selected, "size": size, "samples": samples, "device": args.device,
               "cache_key": cache_key, "source_sha256": file_hash(source) if source else None}
    engine = args.engine
    engine_hint = out/"preview-engine.json"
    if engine == "AUTO":
        engine = "WORKBENCH" if args.stage == "preview" else "CYCLES"
        if args.stage == "preview" and engine_hint.is_file():
            engine = json.loads(engine_hint.read_text()).get("engine", "WORKBENCH")
    engines = [engine]
    if args.engine == "AUTO" and args.stage == "preview" and engine != "CYCLES":
        engines.append("CYCLES")
    start = time.monotonic()
    for engine in engines:
        request["engine"] = engine
        job = out/(args.stage+"-request.json")
        job.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        command = [find_blender(args.blender), "-b", "--factory-startup"]
        if source:
            command.append(str(source))
        command += ["--python-exit-code", "1", "-P", str(scripts/"blender_worker.py"), "--", str(job)]
        log = out/(args.stage+".log")
        emit(stage=args.stage, status="running", engine=engine, log=str(log))
        with log.open("w") as stream:
            child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = child.wait()
            except KeyboardInterrupt:
                import signal
                os.killpg(child.pid, signal.SIGTERM)
                child.wait()
                raise
        if code == 0:
            break
        tail = '\n'.join(log.read_text(errors="replace").splitlines()[-15:])
        if engine == engines[-1]:
            raise RuntimeError(f"Blender exited with {code}; see {log}\n{tail}")
        emit(status="retry", reason="Preview graphics backend failed; trying low-sample Cycles", log=str(log))
    result = json.loads(result_file.read_text())
    if result.get("cache_key") != cache_key:
        raise RuntimeError("Worker result does not match this request")
    if args.stage == "preview":
        engine_hint.write_text(json.dumps({"engine": engine}))
        result["proofs"] = contact_sheet(result, out)
    result["scene_sha256"] = file_hash(dest)
    for entry in result.get("renders", []):
        entry["sha256"] = file_hash(entry["image"])
    result["elapsed_seconds"] = round(time.monotonic()-start, 3)
    result_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    emit(ok=True, cached=False, elapsed_seconds=result["elapsed_seconds"], result=str(result_file),
         scene=str(dest), proofs=result.get("proofs"), images=[e["image"] for e in result.get("renders", [])])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, RuntimeError, OSError) as exc:
        emit(ok=False, error=str(exc))
        sys.exit(1)
