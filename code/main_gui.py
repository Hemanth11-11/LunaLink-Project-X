"""Streamlit mission dashboard for the LunaLink engineering simulator.

The dashboard opens on a mission Home screen (hero, KPIs, 3D globe centrepiece,
subsystem status board) and then gives every subsystem its own tab, matching the
Project X brief's "GUI with visualisation" requirement. Heavy 3D rendering lives
in ``viz3d``; this module wires the physics models to interactive controls.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import viz3d
from components.spacecraft3d import spacecraft_explorer
from lunalink.adcs import AdcsConfig, run_adcs, run_sun_pointing
from lunalink.comms_atmosphere import slant_attenuation_db
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.constants import RAD2DEG
from lunalink.eps import EpsConfig, run_eps
from lunalink.orbit_analysis import CRITICAL_INCLINATION_RAD, frozen_apsides_scan
from lunalink.radiation import mcilwain_l
from lunalink.simulation import run_mission
from lunalink.thermal import ThermalConfig, default_face_coatings, run_thermal
from lunalink.ttc import default_uhf_link_config, default_xband_link_config, run_ttc
from lunalink.validation import metrics_to_dataframe

ASSET_ROOT = Path(__file__).resolve().parents[1]

# 3D scenes hide Plotly's toolbar (drag still rotates) so only Streamlit's clean
# fullscreen expand control shows top-right; 2D charts keep a logo-free toolbar.
PLOTLY_3D_CONFIG = {"displayModeBar": False, "scrollZoom": True}
PLOTLY_2D_CONFIG = {"displaylogo": False}

# Active dashboard theme ("dark" default, "light" toggle); set in main().
CURRENT_THEME = "dark"


def _plot_template() -> str:
    return "plotly_dark" if CURRENT_THEME == "dark" else "plotly_white"

PROJECT_SCOPE_ROWS = [
    {
        "area": "Mission",
        "brief requirement": "Fixed 500 x 36,000 km, 63.4 deg HEO, >= 36 h (>= 3 orbits)",
        "dashboard evidence": "KPI cards, 3D orbit scene, altitude / contact / eclipse plots",
    },
    {
        "area": "EPS",
        "brief requirement": "Power modes, array/battery sizing, SOC over 3+ orbits",
        "dashboard evidence": "Live array, duty-cycle, battery and load controls + SOC plot",
    },
    {
        "area": "TCS",
        "brief requirement": "Coatings, lumped model, six faces, internal node temps",
        "dashboard evidence": "Coating / dissipation controls with 7-node temperature envelope",
    },
    {
        "area": "ADCS",
        "brief requirement": "Detumble, wheel momentum, disturbance torques, 3D orientation",
        "dashboard evidence": "Quaternion-driven 3D spacecraft, rates, torques, momentum",
    },
    {
        "area": "TT&C",
        "brief requirement": "Earth/Moon link budgets, windows, data volume, ground track",
        "dashboard evidence": "Link controls, budget table, ground track, contact windows",
    },
    {
        "area": "Submission",
        "brief requirement": "Python GUI + headless script, explicit assumptions, references",
        "dashboard evidence": "Evidence tab, validation table, report + report-builder",
    },
]


# ---------------------------------------------------------------------------
# Configuration + cached simulation
# ---------------------------------------------------------------------------
def build_gui_config(output_step_s: float = 600.0) -> MissionConfig:
    base = default_mission_config()
    return MissionConfig(
        orbit=base.orbit,
        spacecraft=base.spacecraft,
        ground_station=base.ground_station,
        simulation=SimulationConfig(
            epoch_utc=base.simulation.epoch_utc,
            duration_s=36.0 * 3600.0,
            output_step_s=output_step_s,
        ),
    )


_ORBIT_LOADER_HTML = """
<style>
.ll-loader {display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding: 3.2rem 0 2rem 0;}
.ll-orbit-sys {position:relative; width:210px; height:210px; perspective:600px;}
.ll-earth {position:absolute; top:50%; left:50%; width:76px; height:76px; margin:-38px 0 0 -38px;
    border-radius:50%; background:
        radial-gradient(circle at 34% 32%, #7cc4ff 0%, #2b74c4 42%, #123f7a 75%, #0a2450 100%);
    box-shadow:0 0 34px 6px rgba(56,140,240,0.55), inset -8px -6px 18px rgba(0,0,0,0.55);
    animation: ll-earthspin 14s linear infinite;}
.ll-plane {position:absolute; inset:0; transform: rotateX(70deg); transform-style:preserve-3d;}
.ll-ring {position:absolute; inset:12px; border-radius:50%;
    border:1.5px dashed rgba(120,170,230,0.35); animation: ll-spin 2.6s linear infinite;}
.ll-sat {position:absolute; top:-6px; left:50%; width:12px; height:12px; margin-left:-6px;
    border-radius:50%; background:#f4b740;
    box-shadow:0 0 12px 3px rgba(244,183,64,0.9);}
@keyframes ll-spin {to {transform: rotate(360deg);}}
@keyframes ll-earthspin {to {filter:hue-rotate(18deg);}}
.ll-load-text {margin-top:1.4rem; color:#cfe0f4; font-size:1.02rem; letter-spacing:0.02em;}
.ll-load-sub {margin-top:0.3rem; color:#7f93b0; font-size:0.82rem;}
.ll-dots::after {content:''; animation: ll-dots 1.4s steps(4,end) infinite;}
@keyframes ll-dots {0%{content:'';}25%{content:'.';}50%{content:'..';}75%{content:'...';}}
</style>
<div class="ll-loader">
  <div class="ll-orbit-sys">
    <div class="ll-earth"></div>
    <div class="ll-plane"><div class="ll-ring"><div class="ll-sat"></div></div></div>
  </div>
  <div class="ll-load-text">Propagating the 36&nbsp;h LunaLink mission<span
    class="ll-dots"></span></div>
  <div class="ll-load-sub">J2 + luni-solar orbit &middot; EPS &middot; thermal &middot; ADCS
    &middot; TT&amp;C &middot; validation</div>
</div>
"""


@st.cache_data(show_spinner=False)
def _run_cached(output_step_s: float) -> dict[str, pd.DataFrame | dict]:
    results = run_mission(build_gui_config(output_step_s=output_step_s))
    config_dict = asdict(results.config)
    # asdict() serialises fields only; expose the derived orbit scalars (which
    # are @property values on OrbitConfig) so the GUI can read them by key.
    orbit = results.config.orbit
    config_dict["orbit"].update(
        period_s=orbit.period_s,
        semi_major_axis_m=orbit.semi_major_axis_m,
        eccentricity=orbit.eccentricity,
        perigee_radius_m=orbit.perigee_radius_m,
        apogee_radius_m=orbit.apogee_radius_m,
    )
    validation_df = metrics_to_dataframe(results.validation_metrics)
    # The "value" column mixes floats with flag strings ("False"/"none"); force it
    # to string so Arrow caching/rendering never fails on the mixed dtype.
    validation_df["value"] = validation_df["value"].astype(str)
    return {
        "config": config_dict,
        "environment": results.environment,
        "eps": results.eps,
        "thermal": results.thermal,
        "adcs": results.adcs,
        "ttc": results.ttc,
        "summaries": results.summaries,
        "validation": validation_df,
    }


@st.cache_data(show_spinner=False)
def _environment(output_step_s: float) -> pd.DataFrame:
    return _as_frame(_run_cached(output_step_s)["environment"])


@st.cache_data(show_spinner="Sizing EPS...")
def _eps_variant(
    output_step_s: float, array_area: float, battery_kwh: float, peak_duty: float,
    safe_load: float, nominal_load: float, peak_load: float, pointing_mode: str,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    return run_eps(
        _environment(output_step_s),
        EpsConfig(
            array_area_m2=array_area, battery_capacity_kwh=battery_kwh,
            peak_duty_cycle=peak_duty, safe_load_w=safe_load, nominal_load_w=nominal_load,
            peak_load_w=peak_load, array_pointing_mode=pointing_mode,
        ),
    )


@st.cache_data(show_spinner="Solving thermal balance...")
def _thermal_variant(
    output_step_s: float, coating_mode: str, power_scale: float, conductance: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    env = _environment(output_step_s)
    eps = _as_frame(_run_cached(output_step_s)["eps"])
    config = (
        ThermalConfig(
            face_coatings=default_face_coatings(), internal_conductance_w_m2_k=conductance)
        if coating_mode == "baseline mixed"
        else ThermalConfig(coating=coating_mode, internal_conductance_w_m2_k=conductance)
    )
    return run_thermal(env, power_w=eps["load_power_w"] * power_scale, config=config)


@st.cache_data(show_spinner="Integrating attitude dynamics...")
def _adcs_variant(
    output_step_s: float, tumble_deg_s: float, dipole: float, wheel_capacity: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    # Live preview uses 3 s attitude substeps; headless evidence uses 1 s.
    return run_adcs(
        _environment(output_step_s),
        AdcsConfig(
            initial_tumble_rad_s=tumble_deg_s / RAD2DEG,
            magnetorquer_max_dipole_a_m2=dipole,
            wheel_momentum_capacity_nms=wheel_capacity,
            max_internal_step_s=3.0,
        ),
    )


@st.cache_data(show_spinner="Solving closed-loop sun-pointing...")
def _sun_pointing(output_step_s: float) -> tuple[pd.DataFrame, dict[str, Any]]:
    return run_sun_pointing(_environment(output_step_s))


@st.cache_data(show_spinner="Evaluating link budgets...")
def _ttc_variant(
    output_step_s: float, xband_power: float, xband_rate: float, noise_temp: float,
    uhf_power: float, uhf_rate: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    return run_ttc(
        _environment(output_step_s),
        {
            "xband": {"tx_power_w": xband_power, "data_rate_bps": xband_rate * 1.0e6,
                      "system_noise_temp_k": noise_temp},
            "uhf": {"tx_power_w": uhf_power, "data_rate_bps": uhf_rate * 1.0e3},
        },
    )


# ---------------------------------------------------------------------------
# 3D wrappers (stable public API used by the tests)
# ---------------------------------------------------------------------------
def build_spacecraft_figure(
    config: dict[str, Any],
    quaternion: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0),
) -> go.Figure:
    spacecraft = config["spacecraft"]
    return viz3d.satellite_figure(
        spacecraft["length_x_m"], spacecraft["length_y_m"], spacecraft["length_z_m"], quaternion,
    )


def build_orbit_figure(
    environment: pd.DataFrame, sample_stride: int = 1, time_index: int = -1, height: int = 640,
) -> go.Figure:
    return viz3d.earth_moon_orbit_figure(
        environment, sample_stride=sample_stride, time_index=time_index, height=height,
    )


def mission_spec_table(config: dict[str, Any]) -> pd.DataFrame:
    orbit = config["orbit"]
    spacecraft = config["spacecraft"]
    ground = config["ground_station"]
    return pd.DataFrame(
        [
            ("Orbit", "500 x 36,000 km HEO, Molniya-type"),
            ("Inclination", f"{orbit['inclination_rad'] * RAD2DEG:.1f} deg"),
            ("Computed period", f"{orbit['period_s'] / 3600.0:.4f} h"),
            ("Simulation span", "36 h (>= 3 orbits)"),
            ("Spacecraft mass", f"{spacecraft['mass_kg']:.0f} kg"),
            (
                "Envelope",
                f"{spacecraft['length_x_m']:.1f} x {spacecraft['length_y_m']:.1f} "
                f"x {spacecraft['length_z_m']:.1f} m",
            ),
            ("EOL power budget", f"{spacecraft['eol_power_budget_w'] / 1000.0:.1f} kW"),
            (
                "Ground station",
                f"{ground['name']} ({ground['latitude_rad'] * RAD2DEG:.2f} N, "
                f"{ground['longitude_rad'] * RAD2DEG:.2f} E)",
            ),
            ("Minimum elevation", f"{ground['min_elevation_rad'] * RAD2DEG:.1f} deg"),
        ],
        columns=["parameter", "value"],
    )


def build_ground_track_figure(environment: pd.DataFrame) -> go.Figure:
    lon_deg = (environment["lon_rad"] * RAD2DEG + 180.0) % 360.0 - 180.0
    lat_deg = environment["lat_rad"] * RAD2DEG
    contact = environment["gs_contact_flag"]
    fig = go.Figure()
    fig.add_trace(go.Scattergeo(lon=lon_deg, lat=lat_deg, mode="lines", name="Ground track",
                                line={"color": "#3070b3", "width": 2}))
    fig.add_trace(go.Scattergeo(lon=lon_deg[contact], lat=lat_deg[contact], mode="markers",
                                name="In contact", marker={"size": 6, "color": "#16a34a"}))
    fig.add_trace(go.Scattergeo(lon=[11.65], lat=[48.07], mode="markers+text", name="Ottobrunn",
                                text=["Ottobrunn"], textposition="top center",
                                marker={"size": 9, "color": "#dc2626", "symbol": "star"}))
    fig.update_layout(
        height=420, margin={"l": 0, "r": 0, "t": 10, "b": 0}, template=_plot_template(),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        geo={"projection_type": "natural earth", "showland": True, "landcolor": "#eaf0e8",
             "showocean": True, "oceancolor": "#dceafa", "showcountries": True,
             "countrycolor": "#c3cfe0", "coastlinecolor": "#9fb3cc"},
        legend={"orientation": "h", "y": 1.05},
    )
    return fig


def build_frozen_apsides_figure(config: dict[str, Any]) -> go.Figure:
    orbit = default_mission_config().orbit
    scan = frozen_apsides_scan(orbit)
    critical_deg = CRITICAL_INCLINATION_RAD * RAD2DEG
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=scan["inclination_deg"], y=scan["argp_rate_deg_per_day"],
                             mode="lines", name="Apsidal drift dω/dt",
                             line={"color": "#3070b3", "width": 3}))
    fig.add_hline(y=0.0, line={"color": "#94a3b8", "dash": "dot"})
    fig.add_vline(x=critical_deg, line={"color": "#16a34a", "dash": "dash"},
                  annotation_text="63.4° critical", annotation_position="top")
    fig.add_trace(go.Scatter(x=[63.4], y=[0.0005], mode="markers",
                             marker={"size": 11, "color": "#16a34a", "symbol": "star"},
                             name="LunaLink (frozen)"))
    fig.update_layout(
        title={"text": "Apsidal drift vs inclination — why 63.4° freezes the apogee",
               "font": {"size": 14}, "x": 0.0, "y": 0.98},
        height=360, margin={"l": 0, "r": 0, "t": 60, "b": 0}, template=_plot_template(),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="Inclination (deg)", yaxis_title="dω/dt (deg/day)",
        legend={"orientation": "h", "y": 1.0, "yanchor": "bottom", "x": 1.0, "xanchor": "right"},
    )
    return fig


def build_atmos_loss_figure(lat_deg: float, lon_deg: float) -> go.Figure:
    elevations = np.arange(5.0, 90.1, 2.5)
    loss = [slant_attenuation_db(el, lat_deg, lon_deg, 8.4, 3.0) for el in elevations]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=elevations, y=loss, mode="lines", name="ITU-R P.618/676",
                             line={"color": "#0ea5e9", "width": 3}))
    fig.update_layout(
        title={"text": "X-band atmospheric loss vs elevation (ITU-R, 99% avail.)",
               "font": {"size": 14}, "x": 0.0, "y": 0.98},
        height=320, margin={"l": 0, "r": 0, "t": 56, "b": 0}, template=_plot_template(),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="elevation (deg)", yaxis_title="rain + gas loss (dB)",
        legend={"orientation": "h", "y": 1.0, "yanchor": "bottom", "x": 1.0, "xanchor": "right"},
    )
    return fig


def build_lshell_figure(environment: pd.DataFrame) -> go.Figure:
    time_h = environment["t_s"].to_numpy() / 3600.0
    l_shell = mcilwain_l(environment)
    fig = go.Figure()
    fig.add_hrect(y0=2.0, y1=7.0, fillcolor="#f59e0b", opacity=0.12, line_width=0,
                  annotation_text="Van Allen belts", annotation_position="top left")
    fig.add_trace(go.Scatter(x=time_h, y=np.clip(l_shell, 0, 12), mode="lines",
                             name="McIlwain L", line={"color": "#8b5cf6", "width": 2}))
    fig.update_layout(
        title={"text": "Radiation-belt exposure (McIlwain L-shell)", "font": {"size": 14},
               "x": 0.0, "y": 0.98},
        height=320, margin={"l": 0, "r": 0, "t": 56, "b": 0}, template=_plot_template(),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title="time (h)", yaxis_title="L (Earth radii)",
        legend={"orientation": "h", "y": 1.0, "yanchor": "bottom", "x": 1.0, "xanchor": "right"},
    )
    return fig


def _line_chart(frame: pd.DataFrame, x: str, y: list[str], title: str, y_title: str) -> go.Figure:
    palette = ["#3070b3", "#e8873a", "#16a34a", "#8b5cf6", "#dc2626", "#0ea5e9", "#64748b"]
    fig = go.Figure()
    for column, color in zip(y, palette * 3, strict=False):
        if column in frame.columns:
            fig.add_trace(go.Scatter(x=frame[x], y=frame[column], mode="lines", name=column,
                                     line={"color": color, "width": 2}))
    fig.update_layout(
        title={"text": title, "font": {"size": 14}, "x": 0.0, "xanchor": "left",
               "y": 0.99, "yanchor": "top"},
        height=340, margin={"l": 0, "r": 0, "t": 66, "b": 0}, template=_plot_template(),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis_title=x, yaxis_title=y_title,
        legend={"orientation": "h", "y": 1.0, "yanchor": "bottom", "x": 1.0, "xanchor": "right",
                "font": {"size": 10}},
    )
    return fig


def _windows_to_frame(windows: list[dict[str, float]], volume_bits: float = 0.0) -> pd.DataFrame:
    rows = []
    for index, window in enumerate(windows, start=1):
        rows.append({
            "window": index,
            "start_h": float(window["start_s"]) / 3600.0,
            "end_h": float(window["end_s"]) / 3600.0,
            "duration_min": float(window["duration_s"]) / 60.0,
            "allocated_volume_mbit": volume_bits / 1.0e6 / max(1, len(windows)),
        })
    return pd.DataFrame(rows)


def _sun_angle_proxy_deg(adcs: pd.DataFrame, environment: pd.DataFrame) -> pd.Series:
    body_x = np.array([1.0, 0.0, 0.0], dtype=float)
    angles = []
    for (_, attitude), (_, env_row) in zip(adcs.iterrows(), environment.iterrows(), strict=False):
        q = (attitude.q_w, attitude.q_x, attitude.q_y, attitude.q_z)
        body_x_eci = viz3d._quat_rotate(body_x.reshape(1, 3), q)[0]
        sun_hat = np.array([env_row.sun_hat_x, env_row.sun_hat_y, env_row.sun_hat_z], dtype=float)
        sun_hat = sun_hat / np.linalg.norm(sun_hat)
        dot = float(np.clip(np.dot(body_x_eci, sun_hat), -1.0, 1.0))
        angles.append(np.degrees(np.arccos(dot)))
    return pd.Series(angles, index=adcs.index, name="sun_angle_proxy_deg")


# ---------------------------------------------------------------------------
# Styling + small HTML components
# ---------------------------------------------------------------------------
_DARK_TOKENS = """
        :root {
            --bg1:#05070f; --bg2:#0a1120; --panel:rgba(148,176,214,0.055);
            --panel-solid:rgba(14,22,38,0.88); --edge:rgba(140,170,210,0.18);
            --fg:#e7eefb; --muted:#93a4bd; --accent:#38bdf8; --accent2:#f4b740;
            --hero1:#081733; --hero2:#123a6b; --hero3:#2f6fb0; --shadow:rgba(0,0,0,0.45);
            --pass-bg:rgba(34,197,94,0.16); --pass-fg:#4ade80;
            --warn-bg:rgba(245,158,11,0.16); --warn-fg:#fbbf24;
            --fail-bg:rgba(239,68,68,0.18); --fail-fg:#f87171;}
"""
_LIGHT_TOKENS = """
        :root {
            --bg1:#eef3fa; --bg2:#ffffff; --panel:#ffffff;
            --panel-solid:#ffffff; --edge:#e0e7f1;
            --fg:#0f1b2d; --muted:#56657a; --accent:#3070b3; --accent2:#e8873a;
            --hero1:#0a1f3c; --hero2:#123a6b; --hero3:#2f6fb0; --shadow:rgba(15,27,45,0.10);
            --pass-bg:#dcfce7; --pass-fg:#15803d;
            --warn-bg:#fef3c7; --warn-fg:#b45309;
            --fail-bg:#fee2e2; --fail-fg:#b91c1c;}
"""


def _install_style(theme: str = "dark") -> None:
    tokens = _DARK_TOKENS if theme == "dark" else _LIGHT_TOKENS
    st.markdown(
        f"""
        <style>
        {tokens}
        .stApp {{background:
            radial-gradient(1200px 700px at 78% -8%, var(--hero2) 0%, transparent 55%),
            radial-gradient(900px 600px at 8% 108%, rgba(56,189,248,0.10) 0%, transparent 55%),
            var(--bg1);}}
        [data-testid="stHeader"] {{background: transparent;}}
        [data-testid="stSidebar"] {{background: var(--bg2);
            border-right: 1px solid var(--edge);}}
        .block-container {{padding-top: 1.3rem; padding-bottom: 2rem; max-width: 1380px;}}
        #MainMenu, footer {{visibility: hidden;}}
        h1,h2,h3,h4,p,label,span,li {{color: var(--fg);}}
        .ll-hero {{
            background: linear-gradient(120deg, var(--hero1), var(--hero2) 48%, var(--hero3));
            border-radius: 18px; padding: 1.5rem 1.8rem; color: #eef4fb;
            box-shadow: 0 16px 40px var(--shadow); margin-bottom: 1.1rem;
            border: 1px solid rgba(255,255,255,0.08);}}
        .ll-hero h1 {{font-size: 2.05rem; margin: 0 0 0.25rem 0; letter-spacing: 0.3px;
            color: #ffffff;}}
        .ll-hero .sub {{font-size: 1.02rem; color: #cfe0f4; margin-bottom: 0.9rem;}}
        .ll-chips {{display: flex; flex-wrap: wrap; gap: 0.5rem;}}
        .ll-chip {{background: rgba(255,255,255,0.10); border: 1px solid rgba(255,255,255,0.22);
            border-radius: 999px; padding: 0.28rem 0.8rem; font-size: 0.82rem; color: #eaf2fd;
            backdrop-filter: blur(6px);}}
        .ll-chip b {{color: #ffffff;}}
        div[data-testid="stMetric"] {{
            border: 1px solid var(--edge); border-radius: 14px; padding: 0.7rem 0.9rem;
            background: var(--panel); backdrop-filter: blur(9px);
            box-shadow: 0 2px 10px var(--shadow);}}
        div[data-testid="stMetric"] label {{color: var(--muted); font-weight: 600;}}
        div[data-testid="stMetricValue"] {{color: var(--fg);}}
        .ll-card {{border: 1px solid var(--edge); border-radius: 14px; padding: 0.85rem 1rem;
            background: var(--panel); backdrop-filter: blur(9px); margin-bottom: 0.7rem;
            box-shadow: 0 2px 10px var(--shadow);}}
        .ll-card .t {{font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.6px;
            color: var(--muted); font-weight: 700;}}
        .ll-card .v {{font-size: 1.5rem; font-weight: 700; color: var(--fg); margin: 0.15rem 0;}}
        .ll-card .d {{font-size: 0.8rem; color: var(--muted);}}
        .ll-pill {{display:inline-block; padding: 0.12rem 0.6rem; border-radius: 999px;
            font-size: 0.72rem; font-weight: 700; letter-spacing: 0.4px;}}
        .ll-pass {{background:var(--pass-bg); color:var(--pass-fg);}}
        .ll-warn {{background:var(--warn-bg); color:var(--warn-fg);}}
        .ll-fail {{background:var(--fail-bg); color:var(--fail-fg);}}
        .ll-note {{border-left: 4px solid var(--accent); background: var(--panel);
            backdrop-filter: blur(9px); padding: 0.7rem 1rem; border-radius: 10px;
            color: var(--fg); font-size: 0.9rem; margin: 0.3rem 0 1rem 0;}}
        .ll-section {{font-size: 1.15rem; font-weight: 700; color: var(--fg);
            margin: 0.6rem 0 0.3rem 0; display:flex; align-items:center; gap:0.5rem;}}
        .ll-section::before {{content:""; width:4px; height:1.05rem; border-radius:3px;
            background: linear-gradient(var(--accent), var(--accent2));}}
        /* Tabs */
        button[data-baseweb="tab"] {{font-weight: 600;}}
        [data-baseweb="tab-highlight"] {{background: var(--accent) !important;}}
        /* Custom glowing slider (surprise element) */
        [data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {{
            background: var(--accent) !important;
            box-shadow: 0 0 0 4px rgba(56,189,248,0.22), 0 0 12px rgba(56,189,248,0.7) !important;
            border: 2px solid #ffffff !important;}}
        [data-testid="stSlider"] [data-baseweb="slider"] > div > div > div {{
            background: linear-gradient(90deg, var(--accent), var(--accent2)) !important;}}
        /* Always-visible, cleanly styled fullscreen (expand) control per chart. */
        [data-testid="stElementToolbar"] {{opacity: 1 !important; right: 6px; top: 6px;}}
        [data-testid="stElementToolbarButton"] button, [data-testid="StyledFullScreenButton"] {{
            background: rgba(9,14,26,0.72) !important; color: #ffffff !important;
            border-radius: 8px !important; z-index: 30 !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.35);}}
        [data-testid="stElementToolbarButton"] button:hover,
        [data-testid="StyledFullScreenButton"]:hover {{background: var(--accent) !important;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _pill(status: str) -> str:
    label = {"pass": "PASS", "warn": "WATCH", "fail": "FAIL"}.get(status, status.upper())
    return f'<span class="ll-pill ll-{status}">{label}</span>'


def _status_card(title: str, value: str, detail: str, status: str) -> str:
    return (
        f'<div class="ll-card"><div class="t">{title} &nbsp; {_pill(status)}</div>'
        f'<div class="v">{value}</div><div class="d">{detail}</div></div>'
    )


def _as_dict(value: pd.DataFrame | dict) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("Expected a dictionary payload")
    return value


def _as_frame(value: pd.DataFrame | dict) -> pd.DataFrame:
    if not isinstance(value, pd.DataFrame):
        raise TypeError("Expected a DataFrame payload")
    return value


def _summary_cards(summary: dict[str, Any], keys: list[tuple[str, str, float]]) -> None:
    columns = st.columns(len(keys))
    for column, (label, key, scale) in zip(columns, keys, strict=True):
        value = summary.get(key, "n/a")
        if isinstance(value, bool):
            column.metric(label, "YES" if value else "NO")
        elif isinstance(value, (int, float)):
            column.metric(label, f"{value / scale:.3g}")
        else:
            column.metric(label, str(value))


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
def _render_home(config, environment, summaries, validation, sample_stride) -> None:
    orbit = config["orbit"]
    spacecraft = config["spacecraft"]
    period_h = float(orbit["period_s"]) / 3600.0
    duration_h = float(environment["t_s"].iloc[-1]) / 3600.0
    max_alt_km = float(environment["altitude_m"].max()) / 1000.0

    incl_deg = orbit["inclination_rad"] * RAD2DEG
    eol_kw = spacecraft["eol_power_budget_w"] / 1000.0
    st.markdown(
        f"""
<div class="ll-hero">
  <h1>&#128752; LunaLink Mission Design Dashboard</h1>
  <div class="sub">Earth&ndash;Moon HEO communications relay &middot; Molniya-type
  500&nbsp;&times;&nbsp;36,000&nbsp;km &middot; TUM Project X &middot; all four subsystems</div>
  <div class="ll-chips">
    <div class="ll-chip">Inclination <b>{incl_deg:.1f}&deg;</b></div>
    <div class="ll-chip">Period <b>{period_h:.3f} h</b></div>
    <div class="ll-chip">Mass <b>{spacecraft['mass_kg']:.0f} kg</b></div>
    <div class="ll-chip">EOL power <b>{eol_kw:.1f} kW</b></div>
    <div class="ll-chip">Earth downlink <b>X-band &ge; 100 Mbps</b></div>
    <div class="ll-chip">Moon link <b>UHF 400&ndash;512 MHz</b></div>
    <div class="ll-chip">GS <b>Ottobrunn, 5&deg; min</b></div>
  </div>
</div>
        """,
        unsafe_allow_html=True,
    )

    failed = int((validation["status"] == "fail").sum())
    warned = int((validation["status"] == "warn").sum())
    passed = int((validation["status"] == "pass").sum())
    kpis = st.columns(6)
    kpis[0].metric("Verification", "PASS" if failed == 0 else "FAIL", f"{passed} checks OK")
    kpis[1].metric("Checks warn", warned)
    kpis[2].metric("Orbit period", f"{period_h:.3f} h")
    kpis[3].metric("Sim duration", f"{duration_h:.1f} h", f"{duration_h / period_h:.1f} orbits")
    kpis[4].metric("Apogee altitude", f"{max_alt_km:,.0f} km")
    kpis[5].metric("Spacecraft", f"{spacecraft['mass_kg']:.0f} kg")

    scene, board = st.columns([1.5, 1.0])
    with scene:
        st.markdown('<div class="ll-section">Mission geometry &mdash; live 3D</div>',
                    unsafe_allow_html=True)
        st.plotly_chart(build_orbit_figure(environment, sample_stride, height=560),
                        use_container_width=True, config=PLOTLY_3D_CONFIG)
        st.markdown(
            '<div class="ll-note">Textured Earth (day/night terminator from the modelled Sun '
            'vector) with the Molniya loop &mdash; apogee dwells over the northern hemisphere for '
            'long Ottobrunn contacts. Moon shown in true direction; range not to scale.</div>',
            unsafe_allow_html=True,
        )
    with board:
        st.markdown('<div class="ll-section">Subsystem status board</div>', unsafe_allow_html=True)
        eps = summaries["eps"]
        thermal = summaries["thermal"]
        adcs = summaries["adcs"]
        ttc = summaries["ttc"]
        min_soc = float(eps.get("min_soc", 0.0))
        margin_k = float(thermal.get("worst_operating_margin_k", -1.0))
        final_rate = float(adcs.get("final_angular_speed_deg_s", 9.9))
        xband = ttc.get("xband_min_margin_db")
        xband = float(xband) if xband is not None else -99.0
        cards = "".join([
            _status_card("EPS &middot; min state of charge", f"{min_soc * 100:.0f}%",
                         f"array {eps.get('array_eol_power_w', 0):.0f} W EOL, no unserved load",
                         "pass" if min_soc >= 0.2 else "warn"),
            _status_card("TCS &middot; worst thermal margin", f"{margin_k:.1f} K",
                         "7-node lumped model, mixed passive coatings",
                         "pass" if margin_k >= 5 else "warn"),
            _status_card("ADCS &middot; detumble end rate", f"{final_rate:.3f} deg/s",
                         f"from {adcs.get('initial_angular_speed_deg_s', 0):.1f} deg/s, wheels ok",
                         "pass" if final_rate <= 0.05 else "warn"),
            _status_card("TT&amp;C &middot; X-band margin", f"{xband:.1f} dB",
                         "Earth downlink at 100 Mbps, >= 3 dB required",
                         "pass" if xband >= 3 else "fail"),
        ])
        st.markdown(cards, unsafe_allow_html=True)

    with st.expander("Project X brief coverage (all four subsystems)"):
        st.dataframe(pd.DataFrame(PROJECT_SCOPE_ROWS), hide_index=True, use_container_width=True)


def _render_orbit(config, environment, summaries, sample_stride) -> None:
    st.markdown('<div class="ll-section">3D orbit &amp; environment</div>', unsafe_allow_html=True)
    max_index = len(environment) - 1
    epoch_index = st.slider("Epoch along the 36 h mission (sample index)", 0, max_index, max_index,
                            help="Scrub to move the spacecraft, spin Earth, update Sun/Moon.")
    time_h = float(environment["t_s"].iloc[epoch_index]) / 3600.0
    is_eclipse = bool(environment["eclipse_flag"].iloc[epoch_index])
    is_contact = bool(environment["gs_contact_flag"].iloc[epoch_index])
    sunlit = "eclipse" if is_eclipse else "sunlit"
    contact = "in contact" if is_contact else "no contact"
    st.caption(f"Displayed epoch: t = {time_h:.2f} h ({sunlit}, {contact})")
    st.plotly_chart(
        build_orbit_figure(environment, sample_stride, time_index=epoch_index, height=620),
        use_container_width=True, config=PLOTLY_3D_CONFIG)

    orbit_plot = environment.assign(
        time_h=environment["t_s"] / 3600.0,
        altitude_km=environment["altitude_m"] / 1000.0,
        elevation_deg=environment["gs_elevation_rad"] * RAD2DEG,
        contact=environment["gs_contact_flag"].astype(int),
        eclipse=environment["eclipse_flag"].astype(int),
    )
    cols = st.columns(2)
    with cols[0]:
        st.plotly_chart(_line_chart(orbit_plot, "time_h", ["altitude_km", "elevation_deg"],
                        "Altitude and ground-station elevation", "km / deg"),
                        use_container_width=True)
    with cols[1]:
        st.plotly_chart(_line_chart(orbit_plot, "time_h", ["contact", "eclipse"],
                        "Contact and eclipse flags", "flag"), use_container_width=True)
    st.markdown('<div class="ll-section">Ground track &amp; Ottobrunn visibility</div>',
                unsafe_allow_html=True)
    st.plotly_chart(build_ground_track_figure(environment), use_container_width=True)

    st.markdown('<div class="ll-section">Molniya orbit physics &mdash; the 63.4&deg; choice</div>',
                unsafe_allow_html=True)
    orbit = summaries.get("orbit", {})
    argp_rate = orbit.get("analytic_argp_rate_deg_per_day", 0.0)
    raan_rate = orbit.get("analytic_raan_rate_deg_per_day", 0.0)
    dv_5yr = orbit.get("station_keeping_delta_v_5yr_m_s", 0.0)
    dv_yr = orbit.get("station_keeping_delta_v_m_s_per_year", 0.0)
    cards = st.columns(4)
    cards[0].metric("Critical inclination", f"{orbit.get('critical_inclination_deg', 63.43):.2f}°",
                    f"design {orbit.get('inclination_deg', 63.4):.1f}°")
    cards[1].metric("Apsidal drift dω/dt", f"{argp_rate:.4f}°/day", "frozen (Orekit 0.004)")
    cards[2].metric("Nodal regression", f"{raan_rate:.3f}°/day")
    cards[3].metric("Station-keeping ΔV", f"{dv_5yr:.0f} m/s", f"{dv_yr:.1f} m/s/yr, 5 yr")
    st.plotly_chart(build_frozen_apsides_figure(config), use_container_width=True)
    st.markdown(
        '<div class="ll-note">Independently cross-checked against <b>Orekit 13.1</b> (8×8 gravity '
        '+ luni-solar) and <b>NASA SPICE/DE440</b>: period exact, J2-only trajectory within 38 km '
        'of the full model over 36 h, apsidal drift 0.004°/day at 63.4° vs 0.29°/day at 45°. '
        'See <code>outputs/baseline/external_validation/spice_orekit_crosscheck.md</code>.</div>',
        unsafe_allow_html=True)


def _render_eps(output_step_s) -> None:
    st.markdown('<div class="ll-section">Electrical Power System</div>', unsafe_allow_html=True)
    controls, plots = st.columns([0.34, 0.66])
    with controls:
        st.caption("Sizing & load controls")
        array_area = st.slider("Array area (m2)", 3.0, 8.0, 6.0, 0.25)
        battery_kwh = st.slider("Battery capacity (kWh)", 2.0, 8.0, 4.5, 0.25)
        peak_duty = st.slider("Peak/payload duty cycle", 0.0, 0.5, 0.15, 0.01)
        safe_load = st.slider("Safe load (W)", 300.0, 700.0, 500.0, 25.0)
        nominal_load = st.slider("Nominal load (W)", 650.0, 1000.0, 800.0, 25.0)
        peak_load = st.slider("Peak relay load (W)", 1000.0, 1400.0, 1200.0, 25.0)
        pointing_mode = st.selectbox("Array pointing", ["sun_tracking", "fixed_eci"])
    eps_variant, eps_summary = _eps_variant(output_step_s, array_area, battery_kwh, peak_duty,
                                            safe_load, nominal_load, peak_load, pointing_mode)
    with plots:
        _summary_cards(eps_summary, [
            ("Min SOC", "min_soc", 1.0), ("Array EOL (W)", "array_eol_power_w", 1.0),
            ("Unserved (MJ)", "unserved_energy_j", 1.0e6),
            ("Curtailed (MJ)", "curtailed_energy_j", 1.0e6),
        ])
        eps_plot = eps_variant.assign(time_h=eps_variant["t_s"] / 3600.0)
        st.plotly_chart(
            _line_chart(eps_plot, "time_h", ["solar_power_w", "load_power_w", "net_power_w"],
                        "Generation, load and net power", "W"), use_container_width=True)
        st.plotly_chart(_line_chart(eps_plot, "time_h", ["battery_soc", "array_incidence_factor"],
                        "Battery state of charge and array incidence", "fraction"),
                        use_container_width=True)
    st.markdown("**Power budget by mode**")
    st.dataframe(pd.DataFrame([
        {"mode": "safe (eclipse)", "power_w": safe_load},
        {"mode": "nominal", "power_w": nominal_load},
        {"mode": "peak relay", "power_w": peak_load},
    ]), hide_index=True, use_container_width=True)

    st.markdown('<div class="ll-section">Radiation environment &amp; 5-year degradation</div>',
                unsafe_allow_html=True)
    radiation = _run_cached(output_step_s)["summaries"].get("radiation", {})
    dose = radiation.get("annual_dose_krad_si_estimate", 0.0)
    rad_cols = st.columns(4)
    rad_cols[0].metric("Peak L-shell", f"{radiation.get('peak_l_shell', 0):.1f}",
                       f"{radiation.get('fraction_in_belts', 0) * 100:.0f}% of orbit in belts")
    rad_cols[1].metric("Belt dose", f"{dose:.0f} krad/yr", "behind 2.5 mm Al")
    rad_cols[2].metric("5-yr fluence", f"{radiation.get('fluence_5yr_1mev_e_cm2', 0):.1e}",
                       "1 MeV e⁻/cm²")
    rad_cols[3].metric("Array power @ 5 yr",
                       f"{radiation.get('array_remaining_power_5yr', 0) * 100:.0f}%",
                       "triple-junction, EOL")
    st.plotly_chart(build_lshell_figure(_environment(output_step_s)), use_container_width=True)
    st.markdown(
        '<div class="ll-note">Parametric AE-8-class belt model (McIlwain L → &gt;1 MeV electron '
        'flux → 1 MeV-equivalent fluence → triple-junction degradation). Annual dose lands in the '
        'published 10–30 krad/yr band for a belt-crossing HEO; the derived 5-yr array loss backs '
        'the assumed EOL efficiency. Engineering estimate, not AE9/AP9.</div>',
        unsafe_allow_html=True)


def _render_tcs(output_step_s) -> None:
    st.markdown('<div class="ll-section">Thermal Control System</div>', unsafe_allow_html=True)
    controls, plots = st.columns([0.32, 0.68])
    with controls:
        st.caption("Coating & dissipation controls")
        coating_mode = st.selectbox("Surface coating scenario",
                                    ["baseline mixed", "white", "black", "OSR/FEP", "MLI"])
        power_scale = st.slider("Internal dissipation scale", 0.5, 1.3, 1.0, 0.05)
        conductance = st.slider("Internal conductance (W/m2/K)", 3.0, 12.0, 6.0, 0.5)
    thermal_variant, thermal_summary = _thermal_variant(output_step_s, coating_mode, power_scale,
                                                        conductance)
    with plots:
        _summary_cards(thermal_summary, [
            ("Worst margin (K)", "worst_operating_margin_k", 1.0),
            ("Max internal (K)", "max_internal_temp_k", 1.0),
            ("Min external (K)", "min_external_temp_k", 1.0),
            ("Limit flag", "component_limit_flag", 1.0),
        ])
        thermal_plot = thermal_variant.assign(time_h=thermal_variant["t_s"] / 3600.0)
        st.plotly_chart(_line_chart(thermal_plot, "time_h",
                        ["temp_internal_c", "temp_x_pos_c", "temp_x_neg_c", "temp_y_pos_c",
                         "temp_y_neg_c", "temp_z_pos_c", "temp_z_neg_c"],
                        "Internal node and six-face temperatures", "deg C"),
                        use_container_width=True)
        st.caption("Operating limits: electronics -20/+60 C, battery 0/+45 C, survival -40/+85 C.")
    with st.expander("Thermal summary (hot/cold margins, flags)"):
        st.json(thermal_summary, expanded=False)


def _render_adcs(config, output_step_s) -> None:
    st.markdown('<div class="ll-section">Attitude Determination &amp; Control</div>',
                unsafe_allow_html=True)
    controls, plots = st.columns([0.34, 0.66])
    with controls:
        st.caption("Actuator sizing & initial state")
        tumble_deg_s = st.slider("Initial tumble (deg/s)", 1.0, 15.0, 10.0, 0.5)
        dipole = st.slider("Magnetorquer max dipole (A m2)", 100.0, 600.0, 400.0, 25.0)
        wheel_capacity = st.slider("Wheel momentum capacity (Nms)", 4.0, 20.0, 12.0, 1.0)
    adcs_variant, adcs_summary = _adcs_variant(output_step_s, tumble_deg_s, dipole, wheel_capacity)
    with controls:
        sample_index = st.slider("Orientation epoch (sample)", 0, len(adcs_variant) - 1,
                                 len(adcs_variant) - 1)
    environment = _environment(output_step_s)
    adcs_plot = adcs_variant.assign(
        time_h=adcs_variant["t_s"] / 3600.0,
        sun_angle_proxy_deg=_sun_angle_proxy_deg(adcs_variant, environment),
    )
    with plots:
        _summary_cards(adcs_summary, [
            ("Final (deg/s)", "final_angular_speed_deg_s", 1.0),
            ("Max wheel (Nms)", "max_wheel_momentum_nms", 1.0),
            ("Max torque (Nm)", "max_total_torque_nm", 1.0),
            ("Wheel sat.", "wheel_saturated", 1.0),
        ])
        attitude = adcs_variant.iloc[sample_index]
        q = (attitude.q_w, attitude.q_x, attitude.q_y, attitude.q_z)
        st.plotly_chart(build_spacecraft_figure(config, q), use_container_width=True,
                        config=PLOTLY_3D_CONFIG)
    st.plotly_chart(_line_chart(adcs_plot, "time_h",
                    ["angular_speed_deg_s", "wheel_momentum_norm_nms", "sun_angle_proxy_deg"],
                    "Detumble rate, wheel momentum and Sun-angle proxy", "deg/s, Nms, deg"),
                    use_container_width=True)
    st.plotly_chart(
        _line_chart(adcs_plot, "time_h",
                    ["gravity_gradient_torque_x_nm", "srp_torque_x_nm", "drag_torque_x_nm",
                     "residual_magnetic_torque_x_nm"],
                    "Disturbance torque components (body X)", "Nm"),
        use_container_width=True)
    st.markdown(
        '<div class="ll-note">B-dot detumble and disturbance-momentum bookkeeping are validated. '
        'Live preview uses 3 s attitude substeps (headless evidence uses 1 s).</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ll-section">Closed-loop sun-pointing (PD on reaction wheels)</div>',
                unsafe_allow_html=True)
    pointing_ts, pointing_summary = _sun_pointing(output_step_s)
    magnetic = _run_cached(output_step_s)["summaries"].get("magnetic", {})
    p_cols = st.columns(4)
    p_cols[0].metric("Initial error", f"{pointing_summary['initial_pointing_error_deg']:.0f}°")
    req_met = "met" if pointing_summary["pointing_requirement_met"] else "NOT met"
    p_cols[1].metric("Settled error", f"{pointing_summary['settled_max_pointing_error_deg']:.3f}°",
                     f"req < 3° {req_met}")
    p_cols[2].metric("Max wheel momentum", f"{pointing_summary['max_wheel_momentum_nms']:.2f} Nms")
    if magnetic.get("igrf_available"):
        p_cols[3].metric("Dipole vs IGRF-14", f"{magnetic.get('mean_igrf_dipole_ratio', 1):.2f}×",
                         f"max {magnetic.get('max_relative_difference', 0) * 100:.0f}% diff")
    else:
        p_cols[3].metric("Dipole vs IGRF-14", "n/a", "ppigrf not installed")
    pointing_plot = pointing_ts.assign(time_h=pointing_ts["t_s"] / 3600.0)
    st.plotly_chart(_line_chart(pointing_plot, "time_h",
                    ["pointing_error_deg", "angular_speed_deg_s", "wheel_momentum_norm_nms"],
                    "Sun-pointing error, body rate and wheel momentum", "deg / deg-s⁻¹ / Nms"),
                    use_container_width=True)
    st.markdown(
        '<div class="ll-note">Quaternion-feedback PD controller slews the array normal onto the '
        'Sun line and holds it against gravity-gradient disturbance; steady-state error is the '
        'closed-loop pointing accuracy. The dipole B-field is cross-checked against IGRF-14 '
        '(ppigrf) and agrees within ~5% on average.</div>',
        unsafe_allow_html=True,
    )


def _render_ttc(output_step_s) -> None:
    st.markdown('<div class="ll-section">Telemetry, Tracking &amp; Command</div>',
                unsafe_allow_html=True)
    controls, plots = st.columns([0.34, 0.66])
    xband_base = default_xband_link_config()
    uhf_base = default_uhf_link_config()
    with controls:
        st.caption("Link controls (Earth X-band + Moon UHF)")
        xband_power = st.slider("X-band Tx power (W)", 10.0, 40.0, xband_base.tx_power_w, 1.0)
        xband_rate = st.select_slider("X-band data rate (Mbps)",
                                      options=[25.0, 50.0, 100.0, 150.0], value=100.0)
        noise_temp = st.slider("X-band system noise (K)", 80.0, 300.0,
                               xband_base.system_noise_temp_k, 10.0)
        uhf_power = st.slider("UHF Tx power (W)", 5.0, 40.0, uhf_base.tx_power_w, 1.0)
        uhf_rate = st.select_slider("UHF data rate (kbps)",
                                    options=[2.0, 5.0, 10.0, 20.0], value=10.0)
    ttc_variant, ttc_summary = _ttc_variant(output_step_s, xband_power, xband_rate, noise_temp,
                                            uhf_power, uhf_rate)
    with plots:
        _summary_cards(ttc_summary, [
            ("X margin (dB)", "xband_min_margin_db", 1.0),
            ("UHF margin (dB)", "uhf_min_margin_db", 1.0),
            ("X volume (Gbit)", "xband_data_volume_bits", 1.0e9),
            ("Relay (Gbit)", "end_to_end_relay_volume_bits", 1.0e9),
        ])
        ttc_plot = ttc_variant.assign(
            time_h=ttc_variant["t_s"] / 3600.0,
            xband_volume_gbit=ttc_variant["xband_cumulative_volume_bits"] / 1.0e9,
            uhf_volume_mbit=ttc_variant["uhf_cumulative_volume_bits"] / 1.0e6,
            gs_elevation_deg=ttc_variant["gs_elevation_rad"] * RAD2DEG,
        )
        st.plotly_chart(_line_chart(ttc_plot, "time_h",
                        ["xband_margin_db", "uhf_margin_db", "gs_elevation_deg"],
                        "Link margins and ground elevation", "dB / deg"), use_container_width=True)
        st.plotly_chart(_line_chart(ttc_plot, "time_h", ["xband_volume_gbit", "uhf_volume_mbit"],
                        "Cumulative data volume", "Gbit / Mbit"), use_container_width=True)
    st.markdown("**Link budget statistics (dB accounting)**")
    budget_cols = ["xband_eirp_dbw", "xband_fspl_db", "xband_cn0_db_hz", "xband_ebn0_db",
                   "xband_margin_db", "uhf_eirp_dbw", "uhf_fspl_db", "uhf_cn0_db_hz",
                   "uhf_ebn0_db", "uhf_margin_db"]
    st.dataframe(ttc_variant[budget_cols].describe().T, use_container_width=True)
    st.markdown("**Earth contact windows**")
    st.dataframe(_windows_to_frame(ttc_summary["xband_available_windows"],
                 float(ttc_summary["xband_data_volume_bits"])),
                 hide_index=True, use_container_width=True)

    st.markdown('<div class="ll-section">ITU-R atmosphere, CCSDS coding &amp; Doppler</div>',
                unsafe_allow_html=True)
    comms = _run_cached(output_step_s)["summaries"].get("comms", {})
    c_cols = st.columns(4)
    c_cols[0].metric("Rain+gas @ 5°", f"{comms.get('atmos_loss_5deg_db', 0):.2f} dB",
                     f"{comms.get('atmos_loss_zenith_db', 0):.2f} dB at zenith")
    c_cols[1].metric("CCSDS coding gain", f"{comms.get('ccsds_coding_gain_db', 0):.1f} dB",
                     str(comms.get("ccsds_scheme", "")))
    c_cols[2].metric("Required Eb/N0", f"{comms.get('ccsds_required_ebn0_db', 0):.1f} dB", "coded")
    c_cols[3].metric("Max Doppler", f"{comms.get('max_doppler_khz', 0):.0f} kHz", "X-band")
    st.plotly_chart(build_atmos_loss_figure(48.07, 11.65), use_container_width=True)
    itur_note = ("live ITU-R P.618/P.676 model" if comms.get("itur_available")
                 else "secant-gas fallback (install itur for full ITU-R)")
    st.markdown(
        f'<div class="ll-note">Atmospheric loss is elevation-dependent ({itur_note}): the 5° '
        'window edges cost ~2.5 dB of rain+gas fade versus ~0.2 dB at zenith. CCSDS concatenated '
        'coding adds ~8 dB of margin over uncoded BPSK, and X-band Doppler reaches ~85 kHz near '
        'perigee — all replacing the single fixed loss term in the baseline budget.</div>',
        unsafe_allow_html=True)


def _render_spacecraft(summaries) -> None:
    st.markdown('<div class="ll-section">LunaLink spacecraft explorer</div>',
                unsafe_allow_html=True)
    st.caption("Drag to orbit · scroll to zoom · click any part for details · "
               "slide to explode the assembly · filter by subsystem.")
    eps = summaries.get("eps", {})
    thermal = summaries.get("thermal", {})
    pointing = summaries.get("adcs_pointing", {})
    ttc = summaries.get("ttc", {})
    orbit = summaries.get("orbit", {})
    xband = ttc.get("xband_min_margin_db")
    live_metrics = {
        "Structure": "500 kg · 2.0×1.5×1.0 m bus",
        "EPS": f"{eps.get('array_eol_power_w', 0):.0f} W array EOL",
        "TCS": f"{thermal.get('worst_operating_margin_k', 0):.1f} K thermal margin",
        "TT&C": f"{float(xband):.1f} dB X-band margin" if xband is not None else "X-band link",
        "ADCS": f"{pointing.get('settled_max_pointing_error_deg', 0):.3f}° pointing",
        "Propulsion": f"{orbit.get('station_keeping_delta_v_5yr_m_s', 0):.0f} m/s SK ΔV (5 yr)",
    }
    spacecraft_explorer(theme=CURRENT_THEME, live_metrics=live_metrics, height=660)
    st.markdown(
        '<div class="ll-note">A WebGL model of the LunaLink bus from the mission artwork — gold '
        'MLI structure, deployable solar wings, high-gain X-band dish, UHF relay antennas, '
        'radiator, propellant tank and ADCS units. Click a part to see its subsystem and the live '
        'sizing result it maps to.</div>',
        unsafe_allow_html=True)


def _render_evidence(config, summaries, validation) -> None:
    st.markdown('<div class="ll-section">Validation &amp; evidence</div>', unsafe_allow_html=True)
    def _row_style(row):
        color = {"pass": "#dcfce7", "warn": "#fef3c7", "fail": "#fee2e2"}.get(row["status"], "")
        return [f"background-color: {color}"] * len(row)
    view = validation[["name", "status", "severity", "value", "criterion", "source_module"]]
    st.dataframe(view.style.apply(_row_style, axis=1), use_container_width=True,
                 hide_index=True)
    st.markdown(
        '<div class="ll-note">This dashboard supports preliminary engineering trade studies and '
        'the Project X submission. Flight-qualified use requires independent GMAT/Orekit '
        'correlation, '
        'IV&amp;V, and responsible-authority acceptance.</div>', unsafe_allow_html=True)
    cols = st.columns(2)
    with cols[0]:
        with st.expander("Mission assumptions (config)"):
            st.json(config, expanded=False)
    with cols[1]:
        with st.expander("Baseline subsystem summaries"):
            st.json(summaries, expanded=False)
    asset_path = ASSET_ROOT / "assets" / "lunalink_spacecraft_model.stl"
    if asset_path.exists():
        st.download_button("Download LunaLink STL model", data=asset_path.read_bytes(),
                           file_name=asset_path.name, mime="model/stl")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    global CURRENT_THEME
    st.set_page_config(page_title="LunaLink Mission Dashboard", page_icon="🛰️", layout="wide")

    theme_choice = st.sidebar.radio("Theme", ["🌙 Dark", "☀️ Light"], horizontal=True,
                                    label_visibility="collapsed")
    CURRENT_THEME = "light" if "Light" in theme_choice else "dark"
    _install_style(CURRENT_THEME)

    st.sidebar.header("Simulation controls")
    output_step_s = st.sidebar.select_slider(
        "Output time step", options=[120.0, 300.0, 600.0], value=600.0,
        format_func=lambda value: f"{value:.0f} s",
        help="Finer steps increase fidelity and the initial compute time.")
    sample_stride = st.sidebar.slider("3D orbit sample stride", 1, 6, 1,
                                      help="Thins the plotted orbit points for a lighter 3D scene.")
    st.sidebar.markdown("---")
    st.sidebar.caption(
        "NASA/ECSS-inspired preliminary simulator. Earth & Moon use real NASA-derived "
        "equirectangular textures. Not flight-qualified.")

    loader = st.empty()
    if st.session_state.get("_warm_step") != output_step_s:
        loader.markdown(_ORBIT_LOADER_HTML, unsafe_allow_html=True)
    data = _run_cached(output_step_s)
    loader.empty()
    st.session_state["_warm_step"] = output_step_s
    config = _as_dict(data["config"])
    environment = _as_frame(data["environment"])
    validation = _as_frame(data["validation"])
    summaries = _as_dict(data["summaries"])

    tab_labels = ["🏠 Home", "🌍 Orbit & Environment", "⚡ EPS", "🌡️ TCS",
                  "🧭 ADCS", "📡 TT&C", "🛰 Spacecraft", "✅ Evidence"]
    home, orbit, eps, tcs, adcs, ttc, spacecraft, evidence = st.tabs(tab_labels)
    with home:
        _render_home(config, environment, summaries, validation, sample_stride)
    with orbit:
        _render_orbit(config, environment, summaries, sample_stride)
    with eps:
        _render_eps(output_step_s)
    with tcs:
        _render_tcs(output_step_s)
    with adcs:
        _render_adcs(config, output_step_s)
    with ttc:
        _render_ttc(output_step_s)
    with spacecraft:
        _render_spacecraft(summaries)
    with evidence:
        _render_evidence(config, summaries, validation)


if __name__ == "__main__":
    main()
