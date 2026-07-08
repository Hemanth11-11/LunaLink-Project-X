"""High-fidelity 3D visualisation helpers for the LunaLink dashboard.

This module is imported only by the interactive GUI (``main_gui.py``); the
headless ``main_simulation.py`` never depends on it. It renders

* a texture-mapped, sun-shaded Earth and Moon (real equirectangular maps that
  ship in ``assets/textures/``), and
* a multi-material LunaLink spacecraft driven by the ADCS attitude quaternion.

If the texture assets are missing the sphere falls back to a smooth procedural
colour ramp, so the figures always build (tests and clean installs included).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
from lunalink.constants import EARTH_RADIUS_M, EARTH_ROT_RATE_RAD_S
from numpy.typing import NDArray

# --- geometry constants (kilometres) ---------------------------------------
EARTH_RADIUS_KM = EARTH_RADIUS_M / 1000.0
MOON_RADIUS_KM = 1737.4
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_EARTH_TEXTURE = _PROJECT_ROOT / "assets" / "textures" / "earth_bluemarble.jpg"
_MOON_TEXTURE = _PROJECT_ROOT / "assets" / "textures" / "moon.jpg"

# Space scene palette
_SPACE_BG = "#05070f"
_SUNLIT = "#f4b740"
_ECLIPSE = "#8b7bd8"
_ORBIT = "#38bdf8"
_CONTACT = "#22c55e"
_XBAND = "#38bdf8"
_UHF = "#a3e635"


# ---------------------------------------------------------------------------
# Texture + sphere primitives
# ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _load_texture(path_str: str) -> NDArray[np.uint8] | None:
    """Load an equirectangular texture as an ``(H, W, 3)`` uint8 array."""

    path = Path(path_str)
    if not path.exists():
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


@lru_cache(maxsize=8)
def _uv_sphere(n_lat: int, n_lon: int) -> tuple[NDArray, NDArray, NDArray, NDArray]:
    """Unit sphere as a UV mesh.

    Returns geographic unit vectors ``(N, 3)``, triangle indices ``(M, 3)``,
    and per-vertex texture coordinates ``u`` and ``v`` in ``[0, 1]``.
    """

    lat = np.linspace(np.pi / 2.0, -np.pi / 2.0, n_lat)
    lon = np.linspace(-np.pi, np.pi, n_lon)
    lon_grid, lat_grid = np.meshgrid(lon, lat)
    cos_lat = np.cos(lat_grid)
    x = cos_lat * np.cos(lon_grid)
    y = cos_lat * np.sin(lon_grid)
    z = np.sin(lat_grid)
    vertices = np.column_stack([x.ravel(), y.ravel(), z.ravel()])

    u = (lon_grid.ravel() + np.pi) / (2.0 * np.pi)
    v = (np.pi / 2.0 - lat_grid.ravel()) / np.pi

    faces: list[tuple[int, int, int]] = []
    for i in range(n_lat - 1):
        for j in range(n_lon - 1):
            a = i * n_lon + j
            b = a + 1
            c = a + n_lon
            d = c + 1
            faces.append((a, c, b))
            faces.append((b, c, d))
    return vertices, np.asarray(faces, dtype=int), u, v


def _rot_z(points: NDArray, angle_rad: float) -> NDArray:
    c, s = np.cos(angle_rad), np.sin(angle_rad)
    matrix = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    return points @ matrix.T


def _quat_rotate(points: NDArray, quaternion: tuple[float, float, float, float]) -> NDArray:
    """Rotate ``(N, 3)`` points by a scalar-first quaternion ``[w, x, y, z]``."""

    q = np.asarray(quaternion, dtype=float)
    norm = float(np.linalg.norm(q))
    if norm == 0.0:
        return points.copy()
    q = q / norm
    w, vector = q[0], q[1:4]
    cross_1 = np.cross(vector, points)
    cross_2 = np.cross(vector, cross_1)
    return points + 2.0 * (w * cross_1 + cross_2)


def _sample_texture(
    texture: NDArray[np.uint8] | None, u: NDArray, v: NDArray, fallback: str
) -> NDArray[np.uint8]:
    """Return per-vertex RGB colours from a texture or a procedural fallback."""

    if texture is not None:
        height, width, _ = texture.shape
        col = np.clip((u * (width - 1)).astype(int), 0, width - 1)
        row = np.clip((v * (height - 1)).astype(int), 0, height - 1)
        return texture[row, col].astype(np.uint8)
    # Procedural fallback: latitude ramp so the sphere still reads as a body.
    ramps = {
        "earth": (np.array([13, 40, 84]), np.array([90, 150, 200])),
        "moon": (np.array([70, 70, 74]), np.array([200, 200, 205])),
    }
    low, high = ramps.get(fallback, ramps["moon"])
    t = np.clip(v, 0.0, 1.0)[:, None]
    band = 0.5 + 0.5 * np.sin(v * np.pi * 6.0)[:, None]
    colour = low * (1.0 - t) + high * t
    colour = colour * (0.85 + 0.15 * band)
    return np.clip(colour, 0, 255).astype(np.uint8)


def _shade(
    colours: NDArray[np.uint8],
    normals: NDArray,
    sun_hat: NDArray | None,
    ambient: float = 0.28,
) -> NDArray[np.uint8]:
    """Bake diffuse sun lighting into vertex colours to show a terminator."""

    if sun_hat is None:
        return colours
    sun = sun_hat / (np.linalg.norm(sun_hat) + 1e-12)
    lambert = np.clip(normals @ sun, 0.0, 1.0)
    brightness = np.clip(ambient + (1.0 - ambient) * lambert, 0.0, 1.0)[:, None]
    return np.clip(colours.astype(float) * brightness, 0, 255).astype(np.uint8)


def _textured_body(
    *,
    center_km: NDArray,
    radius_km: float,
    texture_path: Path,
    fallback: str,
    spin_rad: float = 0.0,
    sun_hat: NDArray | None = None,
    ambient: float = 0.28,
    n_lat: int = 60,
    n_lon: int = 120,
    name: str = "body",
) -> go.Mesh3d:
    """Build one texture-mapped, optionally sun-shaded spherical body."""

    unit, faces, u, v = _uv_sphere(n_lat, n_lon)
    texture = _load_texture(str(texture_path))
    colours = _sample_texture(texture, u, v, fallback)
    colours = _shade(colours, unit, sun_hat, ambient=ambient)

    spun = _rot_z(unit, spin_rad)
    points = spun * radius_km + center_km
    return go.Mesh3d(
        x=points[:, 0],
        y=points[:, 1],
        z=points[:, 2],
        i=faces[:, 0],
        j=faces[:, 1],
        k=faces[:, 2],
        vertexcolor=colours,
        lighting={"ambient": 1.0, "diffuse": 0.0, "specular": 0.0},
        flatshading=False,
        hoverinfo="name",
        name=name,
        showscale=False,
    )


def _star_field(radius_km: float, count: int = 360, seed: int = 7) -> go.Scatter3d:
    rng = np.random.default_rng(seed)
    directions = rng.normal(size=(count, 3))
    directions /= np.linalg.norm(directions, axis=1, keepdims=True)
    points = directions * radius_km
    sizes = rng.uniform(0.6, 2.1, size=count)
    return go.Scatter3d(
        x=points[:, 0],
        y=points[:, 1],
        z=points[:, 2],
        mode="markers",
        marker={"size": sizes, "color": "#dbe4ff", "opacity": 0.55},
        hoverinfo="skip",
        showlegend=False,
        name="stars",
    )


# ---------------------------------------------------------------------------
# Orbit scene
# ---------------------------------------------------------------------------
def earth_moon_orbit_figure(
    environment,
    *,
    sample_stride: int = 1,
    time_index: int = -1,
    show_moon: bool = True,
    height: int = 640,
) -> go.Figure:
    """Render the HEO trajectory around a textured, sun-lit Earth.

    The Earth is drawn to scale; the Moon is placed in its true instantaneous
    direction but at a compressed range and exaggerated radius (clearly
    labelled) so the Earth relay geometry stays readable in one frame.
    """

    stride = max(1, int(sample_stride))
    sampled = environment.iloc[::stride].reset_index(drop=True)
    idx = time_index if time_index >= 0 else len(sampled) - 1
    idx = int(np.clip(idx, 0, len(sampled) - 1))
    state = sampled.iloc[idx]

    x_km = sampled["x_eci_m"].to_numpy() / 1000.0
    y_km = sampled["y_eci_m"].to_numpy() / 1000.0
    z_km = sampled["z_eci_m"].to_numpy() / 1000.0
    sc_km = np.array([x_km[idx], y_km[idx], z_km[idx]])

    sun_hat = np.array([state["sun_hat_x"], state["sun_hat_y"], state["sun_hat_z"]], dtype=float)
    spin = EARTH_ROT_RATE_RAD_S * float(state["t_s"])

    fig = go.Figure()
    apogee_km = float(np.max(np.sqrt(x_km**2 + y_km**2 + z_km**2)))
    # Keep the star sphere close to the orbit bounds so aspectmode="data" frames
    # the Earth as a visible globe rather than a distant dot.
    fig.add_trace(_star_field(radius_km=apogee_km * 1.18))

    # Earth (to scale), spun into the ECI frame at the displayed epoch.
    fig.add_trace(
        _textured_body(
            center_km=np.zeros(3),
            radius_km=EARTH_RADIUS_KM,
            texture_path=_EARTH_TEXTURE,
            fallback="earth",
            spin_rad=spin,
            sun_hat=sun_hat,
            ambient=0.4,
            name="Earth",
        )
    )

    # Orbit path, split into sunlit and eclipse samples.
    eclipse = sampled["eclipse_flag"].to_numpy(dtype=bool)
    fig.add_trace(
        go.Scatter3d(
            x=x_km, y=y_km, z=z_km, mode="lines",
            line={"color": _ORBIT, "width": 4},
            name="HEO trajectory", hoverinfo="name",
        )
    )
    if eclipse.any():
        fig.add_trace(
            go.Scatter3d(
                x=x_km[eclipse], y=y_km[eclipse], z=z_km[eclipse], mode="markers",
                marker={"size": 3, "color": _ECLIPSE}, name="Eclipse", hoverinfo="name",
            )
        )
    contact = sampled["gs_contact_flag"].to_numpy(dtype=bool)
    if contact.any():
        fig.add_trace(
            go.Scatter3d(
                x=x_km[contact], y=y_km[contact], z=z_km[contact], mode="markers",
                marker={"size": 3, "color": _CONTACT, "opacity": 0.85, "symbol": "circle"},
                name="Ottobrunn contact", hoverinfo="name",
            )
        )

    # Ground station marker on the spinning globe.
    gs_ecef = _geodetic_unit(np.radians(48.07), np.radians(11.65))
    gs_km = _rot_z(gs_ecef[None, :], spin)[0] * EARTH_RADIUS_KM
    fig.add_trace(
        go.Scatter3d(
            x=[gs_km[0]], y=[gs_km[1]], z=[gs_km[2]], mode="markers+text",
            marker={"size": 4, "color": "#ef4444"}, text=["Ottobrunn"],
            textposition="top center", textfont={"color": "#fca5a5", "size": 10},
            name="Ground station", hoverinfo="name",
        )
    )

    # Spacecraft marker at the displayed epoch.
    fig.add_trace(
        go.Scatter3d(
            x=[sc_km[0]], y=[sc_km[1]], z=[sc_km[2]], mode="markers",
            marker={"size": 6, "color": "#f8fafc", "symbol": "diamond",
                    "line": {"color": "#0ea5e9", "width": 2}},
            name="LunaLink", hoverinfo="name",
        )
    )

    # X-band downlink line when in contact.
    if bool(state["gs_contact_flag"]):
        fig.add_trace(
            go.Scatter3d(
                x=[sc_km[0], gs_km[0]], y=[sc_km[1], gs_km[1]], z=[sc_km[2], gs_km[2]],
                mode="lines", line={"color": _XBAND, "width": 4},
                name="X-band downlink", hoverinfo="name",
            )
        )

    # Moon in its true direction, compressed range, exaggerated size.
    if show_moon:
        moon_hat = np.array(
            [state["moon_hat_x"], state["moon_hat_y"], state["moon_hat_z"]], dtype=float
        )
        moon_hat /= np.linalg.norm(moon_hat) + 1e-12
        # Directional indicator just beyond apogee (true range ~384,000 km is
        # compressed for framing; radius exaggerated for visibility).
        moon_display_km = apogee_km * 1.02
        moon_center = sc_km + moon_hat * moon_display_km
        fig.add_trace(
            _textured_body(
                center_km=moon_center,
                radius_km=EARTH_RADIUS_KM * 0.5,
                texture_path=_MOON_TEXTURE,
                fallback="moon",
                sun_hat=sun_hat,
                ambient=0.32,
                n_lat=40,
                n_lon=80,
                name="Moon (range not to scale)",
            )
        )
        fig.add_trace(
            go.Scatter3d(
                x=[sc_km[0], moon_center[0]], y=[sc_km[1], moon_center[1]],
                z=[sc_km[2], moon_center[2]], mode="lines",
                line={"color": _UHF, "width": 3, "dash": "dash"},
                name="UHF Moon relay", hoverinfo="name",
            )
        )

    # Sun direction indicator.
    sun_end = sc_km + sun_hat * apogee_km * 0.55
    fig.add_trace(
        go.Scatter3d(
            x=[sc_km[0], sun_end[0]], y=[sc_km[1], sun_end[1]], z=[sc_km[2], sun_end[2]],
            mode="lines+markers",
            line={"color": _SUNLIT, "width": 3},
            marker={"size": [0, 6], "color": _SUNLIT, "symbol": "circle"},
            name="Sun direction", hoverinfo="name",
        )
    )

    _apply_space_layout(fig, height=height)
    return fig


def _geodetic_unit(lat_rad: float, lon_rad: float) -> NDArray:
    return np.array(
        [np.cos(lat_rad) * np.cos(lon_rad), np.cos(lat_rad) * np.sin(lon_rad), np.sin(lat_rad)]
    )


def _apply_space_layout(fig: go.Figure, *, height: int) -> None:
    axis = {
        "visible": False,
        "showgrid": False,
        "zeroline": False,
        "showbackground": False,
        "showticklabels": False,
        "title": "",
    }
    fig.update_layout(
        height=height,
        margin={"l": 0, "r": 0, "t": 0, "b": 0},
        paper_bgcolor=_SPACE_BG,
        scene={
            "xaxis": axis,
            "yaxis": axis,
            "zaxis": axis,
            "aspectmode": "data",
            "bgcolor": _SPACE_BG,
            "camera": {"eye": {"x": 1.5, "y": 1.4, "z": 1.0}},
        },
        legend={
            "orientation": "h",
            "y": 0.02,
            "x": 0.5,
            "xanchor": "center",
            "font": {"color": "#cbd5e1", "size": 11},
            "bgcolor": "rgba(5,7,15,0.35)",
        },
        showlegend=True,
    )


# ---------------------------------------------------------------------------
# Spacecraft model
# ---------------------------------------------------------------------------
_MLI_GOLD = "#c9972e"
_MLI_GOLD_DARK = "#9a7320"
_PANEL_BLUE = "#12306e"
_PANEL_CELL = "#2f57a6"
_RADIATOR = "#e8eef5"
_DISH = "#d7dee8"
_STRUCT = "#6b7280"


def _box_mesh(center, size, quaternion, color, opacity=1.0, name="", show=False) -> go.Mesh3d:
    cx, cy, cz = center
    sx, sy, sz = (v / 2.0 for v in size)
    vertices = np.array(
        [
            [cx - sx, cy - sy, cz - sz], [cx + sx, cy - sy, cz - sz],
            [cx + sx, cy + sy, cz - sz], [cx - sx, cy + sy, cz - sz],
            [cx - sx, cy - sy, cz + sz], [cx + sx, cy - sy, cz + sz],
            [cx + sx, cy + sy, cz + sz], [cx - sx, cy + sy, cz + sz],
        ]
    )
    vertices = _quat_rotate(vertices, quaternion)
    tri = np.array(
        [[0, 1, 2], [0, 2, 3], [4, 6, 5], [4, 7, 6], [0, 4, 5],
         [0, 5, 1], [1, 5, 6], [1, 6, 2], [2, 6, 7], [2, 7, 3], [3, 7, 4], [3, 4, 0]]
    )
    return go.Mesh3d(
        x=vertices[:, 0], y=vertices[:, 1], z=vertices[:, 2],
        i=tri[:, 0], j=tri[:, 1], k=tri[:, 2],
        color=color, opacity=opacity, name=name, showlegend=show, hoverinfo="name",
        flatshading=True,
        lighting={"ambient": 0.55, "diffuse": 0.85, "specular": 0.35, "roughness": 0.45},
        lightposition={"x": 2200, "y": 1400, "z": 1600},
    )


def _solar_wing(center, span, quaternion, name, show) -> list[go.BaseTraceType]:
    width_x, width_y, _ = span
    traces: list[go.BaseTraceType] = [
        _box_mesh(center, span, quaternion, _PANEL_BLUE, 0.98, name, show)
    ]
    # Cell grid lines for texture.
    cx, cy, cz = center
    seg = []
    hz = cz + 0.03
    for gx in np.linspace(-width_x / 2.0, width_x / 2.0, 6):
        seg.append([[cx + gx, cy - width_y / 2.0, hz], [cx + gx, cy + width_y / 2.0, hz]])
    for gy in np.linspace(-width_y / 2.0, width_y / 2.0, 9):
        seg.append([[cx - width_x / 2.0, cy + gy, hz], [cx + width_x / 2.0, cy + gy, hz]])
    for segment in seg:
        pts = _quat_rotate(np.array(segment, dtype=float), quaternion)
        traces.append(
            go.Scatter3d(
                x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode="lines",
                line={"color": _PANEL_CELL, "width": 2}, hoverinfo="skip", showlegend=False,
            )
        )
    return traces


def _parabolic_dish(quaternion, lx, show) -> list[go.BaseTraceType]:
    theta = np.linspace(0.0, 2.0 * np.pi, 40)
    radius = np.linspace(0.0, 0.4, 12)
    theta_grid, radius_grid = np.meshgrid(theta, radius)
    depth = 0.2 * (radius_grid / 0.4) ** 2
    local = np.column_stack(
        [
            (lx / 2.0 + 0.5 - depth).ravel(),
            (radius_grid * np.cos(theta_grid)).ravel(),
            (radius_grid * np.sin(theta_grid)).ravel(),
        ]
    )
    n_theta = len(theta)
    faces_i, faces_j, faces_k = [], [], []
    for r in range(len(radius) - 1):
        for t in range(n_theta - 1):
            a = r * n_theta + t
            faces_i.extend([a, a + 1])
            faces_j.extend([a + n_theta, a + n_theta + 1])
            faces_k.extend([a + 1, a + n_theta])
    dish = _quat_rotate(local, quaternion)
    boom_local = np.array([[lx / 2.0, 0, 0], [lx / 2.0 + 0.55, 0, 0]], dtype=float)
    boom = _quat_rotate(boom_local, quaternion)
    return [
        go.Mesh3d(
            x=dish[:, 0], y=dish[:, 1], z=dish[:, 2], i=faces_i, j=faces_j, k=faces_k,
            color=_DISH, opacity=0.96, name="High-gain antenna", showlegend=show,
            hoverinfo="name", flatshading=True,
            lighting={"ambient": 0.6, "diffuse": 0.8, "specular": 0.5, "roughness": 0.3},
            lightposition={"x": 2000, "y": 1400, "z": 1600},
        ),
        go.Scatter3d(
            x=boom[:, 0], y=boom[:, 1], z=boom[:, 2], mode="lines",
            line={"color": _STRUCT, "width": 5}, hoverinfo="skip", showlegend=False,
        ),
    ]


def _uhf_antennas(quaternion, lx, ly) -> list[go.BaseTraceType]:
    traces = []
    for y_sign in (-1.0, 1.0):
        pts = _quat_rotate(
            np.array(
                [[-lx / 2.0, y_sign * ly / 2.0, 0.0], [-lx / 2.0 - 0.5, y_sign * ly / 2.0, 0.28]],
                dtype=float,
            ),
            quaternion,
        )
        traces.append(
            go.Scatter3d(
                x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode="lines+markers",
                line={"color": _UHF, "width": 4}, marker={"size": 3, "color": _UHF},
                name="UHF antenna", showlegend=y_sign > 0, hoverinfo="name",
            )
        )
    return traces


def _body_axes(quaternion, scale) -> list[go.BaseTraceType]:
    axes = [("+X", [scale, 0, 0], "#ef4444"), ("+Y", [0, scale, 0], "#22c55e"),
            ("+Z", [0, 0, scale], "#3b82f6")]
    traces = []
    for label, end, color in axes:
        pts = _quat_rotate(np.vstack([[0, 0, 0], end]).astype(float), quaternion)
        traces.append(
            go.Scatter3d(
                x=pts[:, 0], y=pts[:, 1], z=pts[:, 2], mode="lines+text",
                text=["", label], textposition="top center", textfont={"size": 11, "color": color},
                line={"color": color, "width": 5}, hoverinfo="skip", showlegend=False,
            )
        )
    return traces


def satellite_figure(
    length_x: float,
    length_y: float,
    length_z: float,
    quaternion: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0),
    *,
    height: int = 470,
    show_axes: bool = True,
) -> go.Figure:
    """Render the LunaLink bus at the given attitude quaternion."""

    lx, ly, lz = float(length_x), float(length_y), float(length_z)
    fig = go.Figure()
    # Central MLI bus + payload deck + radiator.
    fig.add_trace(_box_mesh((0, 0, 0), (lx, ly, lz), quaternion, _MLI_GOLD, 1.0, "MLI bus", True))
    fig.add_trace(_box_mesh((0, 0, lz / 2 + 0.05), (1.55, 1.05, 0.08), quaternion,
                            _MLI_GOLD_DARK, 1.0, "Payload deck", False))
    fig.add_trace(_box_mesh((-lx / 2 - 0.03, 0, 0), (0.05, 0.95, 0.65), quaternion,
                            _RADIATOR, 1.0, "Radiator", True))
    # Deployable solar wings.
    wing_span = (1.9, 2.4, 0.05)
    for wing in _solar_wing((0, ly / 2 + 1.3, 0), wing_span, quaternion, "Solar array", True):
        fig.add_trace(wing)
    for wing in _solar_wing((0, -ly / 2 - 1.3, 0), wing_span, quaternion, "Solar array", False):
        fig.add_trace(wing)
    # Yoke struts.
    for y_sign in (-1.0, 1.0):
        strut = _quat_rotate(
            np.array([[0, y_sign * ly / 2, 0], [0, y_sign * (ly / 2 + 0.35), 0]], dtype=float),
            quaternion,
        )
        fig.add_trace(
            go.Scatter3d(x=strut[:, 0], y=strut[:, 1], z=strut[:, 2], mode="lines",
                        line={"color": _STRUCT, "width": 6}, hoverinfo="skip", showlegend=False)
        )
    # High-gain dish + UHF antennas + star tracker + thrusters.
    for trace in _parabolic_dish(quaternion, lx, True):
        fig.add_trace(trace)
    for trace in _uhf_antennas(quaternion, lx, ly):
        fig.add_trace(trace)
    fig.add_trace(_box_mesh((0.35, 0.4, lz / 2 + 0.12), (0.14, 0.14, 0.2), quaternion,
                            "#1f2937", 1.0, "Star tracker", False))
    for corner in ((lx / 2, ly / 2, -lz / 2), (lx / 2, -ly / 2, -lz / 2)):
        fig.add_trace(
            _box_mesh(corner, (0.1, 0.1, 0.12), quaternion, "#374151", 1.0, "Thruster", False))
    if show_axes:
        for trace in _body_axes(quaternion, scale=max(lx, ly) * 0.9 + 0.6):
            fig.add_trace(trace)

    fig.update_layout(
        height=height,
        margin={"l": 0, "r": 0, "t": 10, "b": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        scene={
            "xaxis": {"title": "Body X (m)", "showbackground": False, "color": "#94a3b8"},
            "yaxis": {"title": "Body Y (m)", "showbackground": False, "color": "#94a3b8"},
            "zaxis": {"title": "Body Z (m)", "showbackground": False, "color": "#94a3b8"},
            "aspectmode": "data",
            "camera": {"eye": {"x": 2.0, "y": 1.7, "z": 1.2}},
        },
        legend={"orientation": "h", "y": 1.02, "font": {"size": 10}},
    )
    return fig
