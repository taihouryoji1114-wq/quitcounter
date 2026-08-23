"""Build the lightweight 大王 Tokyo map from MLIT N03 GeoJSON.

The source file is the official 2026 administrative-boundary dataset.  This
builder intentionally keeps only mainland Tokyo (23 wards and Tama) and turns
the many source fragments into compact SVG paths suitable for mobile play.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


MAINLAND_PREFIXES = ("131", "132")
MAINLAND_TOWNS = {"13303", "13305", "13307", "13308"}


def is_mainland(code: str | None) -> bool:
    return bool(code and (code.startswith(MAINLAND_PREFIXES) or code in MAINLAND_TOWNS))


def polygons(geometry: dict):
    if geometry["type"] == "Polygon":
        yield geometry["coordinates"]
    elif geometry["type"] == "MultiPolygon":
        yield from geometry["coordinates"]


def perpendicular_distance(point, start, end):
    if start == end:
        return math.dist(point, start)
    x, y = point
    x1, y1 = start
    x2, y2 = end
    return abs((y2-y1)*x - (x2-x1)*y + x2*y1 - y2*x1) / math.hypot(y2-y1, x2-x1)


def simplify(points, tolerance=0.00022):
    if len(points) <= 4:
        return points
    closed = points[0] == points[-1]
    work = points[:-1] if closed else points
    if len(work) <= 3:
        return points

    def rdp(chunk):
        if len(chunk) <= 2:
            return chunk
        distances = [perpendicular_distance(p, chunk[0], chunk[-1]) for p in chunk[1:-1]]
        greatest = max(distances, default=0)
        if greatest <= tolerance:
            return [chunk[0], chunk[-1]]
        index = distances.index(greatest) + 1
        return rdp(chunk[:index+1])[:-1] + rdp(chunk[index:])

    # A closed ring needs two anchors; use the point farthest from the first.
    pivot = max(range(1, len(work)), key=lambda i: math.dist(work[0], work[i]))
    result = rdp(work[:pivot+1])[:-1] + rdp(work[pivot:] + [work[0]])
    if result[-1] != result[0]:
        result.append(result[0])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    raw = json.loads(args.source.read_text())
    grouped = defaultdict(list)
    names = {}
    boundary_points = defaultdict(set)
    all_points = []

    for feature in raw["features"]:
        props = feature["properties"]
        code = props.get("N03_007")
        if not is_mainland(code):
            continue
        names[code] = props["N03_004"]
        for polygon in polygons(feature["geometry"]):
            grouped[code].append(polygon)
            for ring in polygon:
                for x, y in ring:
                    boundary_points[code].add((round(x, 6), round(y, 6)))
                    all_points.append((x, y))

    min_x = min(x for x, _ in all_points)
    max_x = max(x for x, _ in all_points)
    min_y = min(y for _, y in all_points)
    max_y = max(y for _, y in all_points)
    width, height = 1200, 650

    def project(point):
        x, y = point
        px = (x-min_x)/(max_x-min_x)*width
        py = height-(y-min_y)/(max_y-min_y)*height
        return round(px, 1), round(py, 1)

    neighbours = {code: [] for code in grouped}
    codes = sorted(grouped)
    for index, code in enumerate(codes):
        for other in codes[index+1:]:
            if len(boundary_points[code] & boundary_points[other]) >= 2:
                neighbours[code].append(other)
                neighbours[other].append(code)

    regions = []
    terrains = ("plain", "forest", "hill", "plain", "plain")
    for index, code in enumerate(codes):
        path_parts = []
        projected_points = []
        for polygon in grouped[code]:
            for ring in polygon:
                reduced = simplify(ring)
                points = [project(point) for point in reduced]
                if len(points) < 4:
                    continue
                projected_points.extend(points)
                path_parts.append("M" + "L".join(f"{x},{y}" for x, y in points) + "Z")
        regions.append({
            "id": code,
            "name": names[code],
            "path": "".join(path_parts),
            "cx": round(sum(x for x, _ in projected_points)/len(projected_points), 1),
            "cy": round(sum(y for _, y in projected_points)/len(projected_points), 1),
            "terrain": terrains[index % len(terrains)],
            "neighbors": sorted(neighbours[code]),
        })

    output = {
        "source": "国土数値情報 行政区域データ N03-2026（2026年1月1日時点）",
        "license": "CC BY 4.0",
        "viewBox": f"0 0 {width} {height}",
        "regions": regions,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    print(f"wrote {len(regions)} regions to {args.output}")


if __name__ == "__main__":
    main()
