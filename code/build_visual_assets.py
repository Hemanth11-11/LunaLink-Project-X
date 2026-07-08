"""Build 3D visual assets for the LunaLink dashboard."""

from __future__ import annotations

import json
from math import cos, pi, sin
from pathlib import Path

Vector = tuple[float, float, float]
Triangle = tuple[Vector, Vector, Vector]


def add_box(
    triangles: list[Triangle],
    center: Vector,
    size: Vector,
) -> None:
    cx, cy, cz = center
    sx, sy, sz = (value / 2.0 for value in size)
    vertices = [
        (cx - sx, cy - sy, cz - sz),
        (cx + sx, cy - sy, cz - sz),
        (cx + sx, cy + sy, cz - sz),
        (cx - sx, cy + sy, cz - sz),
        (cx - sx, cy - sy, cz + sz),
        (cx + sx, cy - sy, cz + sz),
        (cx + sx, cy + sy, cz + sz),
        (cx - sx, cy + sy, cz + sz),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1),
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 4), (3, 4, 0),
    ]
    triangles.extend((vertices[i], vertices[j], vertices[k]) for i, j, k in faces)


def add_dish(
    triangles: list[Triangle],
    center_x: float,
    radius: float,
    depth: float,
    segments: int = 48,
    rings: int = 10,
) -> None:
    grid: list[list[Vector]] = []
    for ring in range(rings + 1):
        radial = radius * ring / rings
        x_value = center_x - depth * (radial / radius) ** 2
        grid.append(
            [
                (x_value, radial * cos(2.0 * pi * index / segments),
                 radial * sin(2.0 * pi * index / segments))
                for index in range(segments)
            ]
        )
    for ring in range(rings):
        for index in range(segments):
            next_index = (index + 1) % segments
            a = grid[ring][index]
            b = grid[ring][next_index]
            c = grid[ring + 1][index]
            d = grid[ring + 1][next_index]
            triangles.append((a, c, b))
            triangles.append((b, c, d))


def write_ascii_stl(path: Path, triangles: list[Triangle]) -> None:
    lines = ["solid lunalink_spacecraft"]
    for triangle in triangles:
        normal = _normal(triangle)
        lines.append(f"  facet normal {normal[0]:.6e} {normal[1]:.6e} {normal[2]:.6e}")
        lines.append("    outer loop")
        for vertex in triangle:
            lines.append(f"      vertex {vertex[0]:.6e} {vertex[1]:.6e} {vertex[2]:.6e}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid lunalink_spacecraft")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _normal(triangle: Triangle) -> Vector:
    a, b, c = triangle
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    norm = (cross[0] ** 2 + cross[1] ** 2 + cross[2] ** 2) ** 0.5
    if norm == 0.0:
        return (0.0, 0.0, 0.0)
    return (cross[0] / norm, cross[1] / norm, cross[2] / norm)


def build_lunalink_stl(output_dir: Path = Path("assets")) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    triangles: list[Triangle] = []
    add_box(triangles, (0.0, 0.0, 0.0), (2.0, 1.5, 1.0))
    add_box(triangles, (0.0, 0.0, 0.545), (1.55, 1.05, 0.08))
    add_box(triangles, (-1.02, 0.0, 0.0), (0.04, 0.92, 0.62))
    add_box(triangles, (0.0, 1.95, 0.0), (1.9, 2.35, 0.045))
    add_box(triangles, (0.0, -1.95, 0.0), (1.9, 2.35, 0.045))
    add_box(triangles, (1.35, 0.0, 0.0), (0.7, 0.045, 0.045))
    add_box(triangles, (-1.22, 0.75, 0.11), (0.46, 0.035, 0.035))
    add_box(triangles, (-1.22, -0.75, 0.11), (0.46, 0.035, 0.035))
    add_dish(triangles, center_x=1.42, radius=0.38, depth=0.18)

    stl_path = output_dir / "lunalink_spacecraft_model.stl"
    write_ascii_stl(stl_path, triangles)
    manifest = {
        "asset": str(stl_path),
        "description": (
            "Project X LunaLink concept model: gold bus, deployable solar panels, "
            "radiator, high-gain dish, and low-gain UHF antennas."
        ),
        "units": "meters",
        "triangle_count": len(triangles),
    }
    (output_dir / "visual_asset_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return stl_path


if __name__ == "__main__":
    print(build_lunalink_stl())
