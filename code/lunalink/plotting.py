"""Matplotlib evidence figures for LunaLink runs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .constants import RAD2DEG
from .io import ensure_directory


def save_basic_figures(
    results: Any,
    output_dir: str | Path,
    trade_df: pd.DataFrame | None = None,
) -> dict[str, str]:
    """Save core evidence plots and return their paths."""

    directory = ensure_directory(Path(output_dir) / "figures")
    figures: dict[str, str] = {}
    figures.update(_save_groundtrack(results.environment, directory))
    figures.update(_save_eclipse_contact(results.environment, directory))
    figures.update(_save_eps(results.eps, directory))
    figures.update(_save_thermal(results.thermal, directory))
    figures.update(_save_adcs(results.adcs, directory))
    figures.update(_save_ttc(results.ttc, directory))
    if trade_df is not None and not trade_df.empty:
        figures.update(_save_pareto(trade_df, directory))
    return figures


def _register(figures: dict[str, str], path: Path) -> dict[str, str]:
    figures[path.name] = str(path)
    return figures


def _time_h(frame: pd.DataFrame) -> np.ndarray:
    return frame["t_s"].to_numpy(dtype=float) / 3600.0


def _save_groundtrack(environment: pd.DataFrame, directory: Path) -> dict[str, str]:
    path = directory / "orbit_groundtrack.png"
    fig, ax = plt.subplots(figsize=(8.0, 4.2), constrained_layout=True)
    lon_deg = environment["lon_rad"].to_numpy(dtype=float) * RAD2DEG
    lat_deg = environment["lat_rad"].to_numpy(dtype=float) * RAD2DEG
    contact = environment["gs_contact_flag"].to_numpy(dtype=bool)
    ax.plot(lon_deg, lat_deg, color="#3366aa", linewidth=1.4, label="subsatellite")
    if np.any(contact):
        ax.scatter(
            lon_deg[contact],
            lat_deg[contact],
            s=18,
            color="#cc4c02",
            label="Ottobrunn contact",
        )
    ax.set_xlabel("Longitude deg")
    ax.set_ylabel("Latitude deg")
    ax.set_title("Ground Track and Contact Samples")
    ax.set_xlim(-180.0, 180.0)
    ax.set_ylim(-90.0, 90.0)
    ax.grid(True, linewidth=0.4, alpha=0.5)
    ax.legend(loc="best")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return _register({}, path)


def _save_eclipse_contact(environment: pd.DataFrame, directory: Path) -> dict[str, str]:
    path = directory / "eclipse_contact_timeline.png"
    fig, ax = plt.subplots(figsize=(8.0, 3.4), constrained_layout=True)
    t_h = _time_h(environment)
    eclipse = environment["eclipse_flag"].astype(int)
    contact = environment["gs_contact_flag"].astype(int)
    ax.step(t_h, eclipse, where="post", label="eclipse", color="#4c78a8")
    ax.step(t_h, contact + 1.2, where="post", label="ground contact", color="#f58518")
    ax.set_yticks([0, 1, 1.2, 2.2], ["sun", "eclipse", "no contact", "contact"])
    ax.set_xlabel("Mission elapsed time h")
    ax.set_title("Eclipse and Ground Contact Timeline")
    ax.grid(True, axis="x", linewidth=0.4, alpha=0.5)
    ax.legend(loc="upper right")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return _register({}, path)


def _save_eps(eps: pd.DataFrame, directory: Path) -> dict[str, str]:
    path = directory / "eps_power_soc.png"
    fig, ax = plt.subplots(figsize=(8.0, 4.0), constrained_layout=True)
    t_h = _time_h(eps)
    ax.plot(t_h, eps["solar_power_w"], label="solar power W", color="#2ca02c")
    ax.plot(t_h, eps["load_power_w"], label="load power W", color="#d62728")
    ax.plot(t_h, eps["net_power_w"], label="net power W", color="#1f77b4", alpha=0.7)
    ax.set_xlabel("Mission elapsed time h")
    ax.set_ylabel("Power W")
    ax.grid(True, linewidth=0.4, alpha=0.5)
    soc_ax = ax.twinx()
    soc_ax.plot(t_h, eps["battery_soc"], label="battery SOC", color="#111111", linewidth=1.8)
    soc_ax.set_ylabel("Battery state of charge")
    ax.set_title("EPS Power Balance")
    lines, labels = ax.get_legend_handles_labels()
    soc_lines, soc_labels = soc_ax.get_legend_handles_labels()
    ax.legend(lines + soc_lines, labels + soc_labels, loc="best")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return _register({}, path)


def _save_thermal(thermal: pd.DataFrame, directory: Path) -> dict[str, str]:
    path = directory / "thermal_faces_internal.png"
    fig, ax = plt.subplots(figsize=(8.0, 4.0), constrained_layout=True)
    t_h = _time_h(thermal)
    ax.plot(t_h, thermal["temp_internal_c"], label="internal C", color="#111111")
    ax.plot(t_h, thermal["temp_min_k"] - 273.15, label="coldest node C", color="#4c78a8")
    ax.plot(t_h, thermal["temp_max_k"] - 273.15, label="hottest node C", color="#e45756")
    ax.set_xlabel("Mission elapsed time h")
    ax.set_ylabel("Temperature C")
    ax.set_title("Thermal Node Envelope")
    ax.grid(True, linewidth=0.4, alpha=0.5)
    ax.legend(loc="best")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return _register({}, path)


def _save_adcs(adcs: pd.DataFrame, directory: Path) -> dict[str, str]:
    path = directory / "adcs_detumble_pointing.png"
    fig, ax = plt.subplots(figsize=(8.0, 4.0), constrained_layout=True)
    t_h = _time_h(adcs)
    ax.semilogy(t_h, adcs["angular_speed_deg_s"], label="angular speed deg/s", color="#6a51a3")
    ax.set_xlabel("Mission elapsed time h")
    ax.set_ylabel("Angular speed deg/s")
    ax.grid(True, linewidth=0.4, alpha=0.5)
    wheel_ax = ax.twinx()
    wheel_ax.plot(
        t_h,
        adcs["wheel_momentum_norm_nms"],
        label="wheel momentum Nms",
        color="#31a354",
        alpha=0.8,
    )
    wheel_ax.set_ylabel("Wheel momentum Nms")
    ax.set_title("ADCS Detumble and Momentum")
    lines, labels = ax.get_legend_handles_labels()
    wheel_lines, wheel_labels = wheel_ax.get_legend_handles_labels()
    ax.legend(lines + wheel_lines, labels + wheel_labels, loc="best")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return _register({}, path)


def _save_ttc(ttc: pd.DataFrame, directory: Path) -> dict[str, str]:
    path = directory / "ttc_range_margin_data.png"
    fig, ax = plt.subplots(figsize=(8.0, 4.0), constrained_layout=True)
    t_h = _time_h(ttc)
    ax.plot(t_h, ttc["xband_margin_db"], label="X-band margin dB", color="#1f77b4")
    ax.plot(t_h, ttc["uhf_margin_db"], label="UHF margin dB", color="#ff7f0e")
    ax.axhline(3.0, color="#444444", linestyle="--", linewidth=1.0, label="3 dB threshold")
    ax.set_xlabel("Mission elapsed time h")
    ax.set_ylabel("Link margin dB")
    ax.grid(True, linewidth=0.4, alpha=0.5)
    data_ax = ax.twinx()
    data_gb = ttc["xband_cumulative_volume_bits"].to_numpy(dtype=float) / 1.0e9
    data_ax.plot(t_h, data_gb, label="X-band data volume Gb", color="#2ca02c", alpha=0.8)
    data_ax.set_ylabel("Cumulative X-band volume Gb")
    ax.set_title("TT&C Link Margin and Data Return")
    lines, labels = ax.get_legend_handles_labels()
    data_lines, data_labels = data_ax.get_legend_handles_labels()
    ax.legend(lines + data_lines, labels + data_labels, loc="best")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return _register({}, path)


def _save_pareto(trade_df: pd.DataFrame, directory: Path) -> dict[str, str]:
    path = directory / "pareto_eps_trade.png"
    fig, ax = plt.subplots(figsize=(6.4, 4.6), constrained_layout=True)
    scatter = ax.scatter(
        trade_df["array_area_m2"],
        trade_df["battery_capacity_kwh"],
        c=trade_df["min_soc"],
        s=80.0,
        cmap="viridis",
        vmin=0.0,
        vmax=1.0,
    )
    ax.set_xlabel("Solar array area m2")
    ax.set_ylabel("Battery capacity kWh")
    ax.set_title("EPS Sizing Trade: Minimum SOC")
    ax.grid(True, linewidth=0.4, alpha=0.5)
    fig.colorbar(scatter, ax=ax, label="Minimum SOC")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return _register({}, path)
