"""Portable project validation and model identity; no Blender dependency."""
import hashlib
import json
import math
import re


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    allow_nan=False).encode()).hexdigest()


def geometry_key(project):
    return digest({k: project.get(k) for k in ("units", "room", "components")})


def positive(value, label, allow_zero=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label}: expected a finite number")
    if not math.isfinite(value) or (value < 0 if allow_zero else value <= 0):
        raise ValueError(f"{label}: invalid dimension {value}")


def vector(value, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label}: expected three coordinates")
    for x in value:
        if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x):
            raise ValueError(f"{label}: non-finite coordinate")


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
        raise ValueError(f"Unsafe or invalid identifier: {value!r}")


def validate(project):
    if project.get("schema_version") != 1 or project.get("units") != "mm":
        raise ValueError("Require schema_version=1 and units=mm")
    if project.get("mode", "build") not in ("build", "existing"):
        raise ValueError("mode must be build or existing")
    room = project.get("room", {})
    if project.get("mode", "build") == "build" and not room:
        raise ValueError("A room is required for building")
    if room:
        for k in ("width_mm", "depth_mm", "height_mm", "wall_mm"):
            positive(room[k], "room." + k)
        if set(room.get("open_sides", ["front"])) - {"left", "right", "front", "back", "ceiling"}:
            raise ValueError("Unknown room open_sides value")
    ids = set()
    for item in project.get("components", []):
        identifier(item["id"])
        if item["id"] in ids:
            raise ValueError("Duplicate component: " + item["id"])
        ids.add(item["id"])
        vector(item["position_mm"], item["id"] + ".position_mm")
        rotation = item.get("rotation_deg", 0)
        if not isinstance(rotation, (int, float)) or not math.isfinite(rotation):
            raise ValueError("Non-finite rotation")
        kind = item["kind"]
        if kind not in ("cabinet", "box", "slats", "prism"):
            raise ValueError("Unknown component kind: " + str(kind))
        if kind == "prism":
            points = item["polygon_mm"]
            if len(points) < 3:
                raise ValueError("A prism needs at least three polygon points")
            for pt in points:
                if len(pt) != 2:
                    raise ValueError("polygon_mm must contain XY pairs")
                vector([*pt, 0], "polygon_mm")
            area = sum(a[0]*b[1]-b[0]*a[1] for a, b in zip(points, points[1:]+points[:1]))
            if abs(area) < 1e-6:
                raise ValueError("Degenerate prism polygon")
            positive(item["height_mm"], "height_mm")
            continue
        for k in ("width_mm", "depth_mm", "height_mm"):
            positive(item[k], item["id"] + "." + k)
        if kind == "slats":
            count = item["count"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise ValueError("slats.count must be a positive integer")
            positive(item["bar_mm"], "bar_mm")
            if count*item["bar_mm"] > item["width_mm"]:
                raise ValueError("Slats are wider than their overall width")
        if kind == "cabinet":
            width, height, depth = (item[k] for k in ("width_mm", "height_mm", "depth_mm"))
            board, door, gap = (item.get(k, d) for k, d in
                                (("board_mm", 18), ("door_mm", 18), ("gap_mm", 3)))
            for x, label in ((board, "board_mm"), (door, "door_mm"), (gap, "gap_mm")):
                positive(x, label)
            if min(width, height) <= 2*board or depth <= door+board+gap:
                raise ValueError("Cabinet has no interior space")
            cols = item["columns"]
            if not cols or abs(sum(c["width_mm"] for c in cols)-width) > 0.1:
                raise ValueError(item["id"] + ": column widths must equal cabinet width")
            for col in cols:
                positive(col["width_mm"], "column width")
                if col["width_mm"] <= max(2*board, gap):
                    raise ValueError("Cabinet column is too narrow")
                rows = col.get("rows_mm", [height])
                if not rows or abs(sum(rows)-height) > 0.1:
                    raise ValueError("Front row heights must equal cabinet height")
                for row in rows:
                    positive(row, "row height")
                    if row <= gap:
                        raise ValueError("Door gap consumes front panel")
                handle = col.get("handle", {"style": "none"})
                if handle.get("style", "none") not in ("none", "bar", "f", "knob"):
                    raise ValueError("Unknown handle style")
                if handle.get("side", "center") not in ("left", "right", "center"):
                    raise ValueError("Unknown handle side")
                if handle.get("orientation", "vertical") not in ("vertical", "horizontal"):
                    raise ValueError("Unknown handle orientation")
                if handle.get("style") == "f" and handle.get("orientation", "vertical") != "vertical":
                    raise ValueError("F handles require vertical orientation")
                positive(handle.get("length_mm", 160), "handle length")
                if handle.get("style") in ("bar", "f"):
                    span = min(rows) if handle.get("orientation", "vertical") == "vertical" else col["width_mm"]
                    if handle.get("length_mm", 160) >= span-gap:
                        raise ValueError("Handle is longer than its front panel")
    camera_ids = set()
    for cam in project.get("cameras", []):
        identifier(cam["id"])
        if cam["id"] in camera_ids:
            raise ValueError("Duplicate camera: " + cam["id"])
        camera_ids.add(cam["id"])
        vector(cam["position_mm"], "camera.position_mm")
        vector(cam["target_mm"], "camera.target_mm")
        if cam["position_mm"] == cam["target_mm"]:
            raise ValueError("Camera position and target coincide")
        positive(cam.get("lens_mm", 28), "lens_mm")
        for k in ("shift_x", "shift_y"):
            value = cam.get(k, 0)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Invalid camera shift")
        aspect = cam.get("aspect", [4, 3])
        if len(aspect) != 2:
            raise ValueError("aspect must contain width and height")
        for v in aspect:
            positive(v, "aspect")
    return project


def load(path):
    with open(path, encoding="utf-8") as stream:
        return validate(json.load(stream))
