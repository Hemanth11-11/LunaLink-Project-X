"""Electrical power subsystem model for LunaLink.

The model consumes the shared Phase 2 environment table and keeps all internal
energy accounting in SI units. Configuration accepts battery capacity in kWh
because that is the common sizing shorthand, then converts it at the boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from numpy.typing import NDArray

J_PER_KWH = 3_600_000.0

REQUIRED_ENVIRONMENT_COLUMNS = {
    "t_s",
    "eclipse_flag",
    "solar_flux_w_m2",
    "sun_hat_x",
    "sun_hat_y",
    "sun_hat_z",
    "gs_contact_flag",
}


@dataclass(frozen=True)
class EpsConfig:
    """Configuration for the simplified electrical power subsystem."""

    array_area_m2: float = 6.0
    eta_eol: float = 0.27
    sun_pointing_efficiency: float = 0.95
    power_conditioning_efficiency: float = 0.92
    array_pointing_mode: str = "sun_tracking"
    array_normal_eci: tuple[float, float, float] = (1.0, 0.0, 0.0)

    safe_load_w: float = 500.0
    nominal_load_w: float = 800.0
    peak_load_w: float = 1_200.0
    peak_duty_cycle: float = 0.15
    peak_cycle_s: float = 3_600.0

    battery_capacity_kwh: float = 4.5
    initial_soc: float = 0.8
    charge_efficiency: float = 0.94
    discharge_efficiency: float = 0.96

    def __post_init__(self) -> None:
        if self.array_area_m2 < 0.0:
            raise ValueError("array_area_m2 must be non-negative.")
        if self.array_pointing_mode not in {"sun_tracking", "fixed_eci"}:
            raise ValueError("array_pointing_mode must be 'sun_tracking' or 'fixed_eci'.")
        if len(self.array_normal_eci) != 3:
            raise ValueError("array_normal_eci must contain three values.")
        if np.linalg.norm(np.asarray(self.array_normal_eci, dtype=float)) == 0.0:
            raise ValueError("array_normal_eci must be non-zero.")
        for name in (
            "eta_eol",
            "sun_pointing_efficiency",
            "power_conditioning_efficiency",
            "charge_efficiency",
            "discharge_efficiency",
        ):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1.")
        if not (0.0 <= self.safe_load_w <= self.nominal_load_w <= self.peak_load_w):
            raise ValueError("loads must satisfy safe_load_w <= nominal_load_w <= peak_load_w.")
        if not 0.0 <= self.peak_duty_cycle <= 1.0:
            raise ValueError("peak_duty_cycle must be between 0 and 1.")
        if self.peak_cycle_s <= 0.0:
            raise ValueError("peak_cycle_s must be positive.")
        if self.battery_capacity_kwh <= 0.0:
            raise ValueError("battery_capacity_kwh must be positive.")
        if not 0.0 <= self.initial_soc <= 1.0:
            raise ValueError("initial_soc must be between 0 and 1.")

    @property
    def battery_capacity_j(self) -> float:
        return self.battery_capacity_kwh * J_PER_KWH


def _require_environment_columns(environment_df: pd.DataFrame) -> None:
    missing = REQUIRED_ENVIRONMENT_COLUMNS.difference(environment_df.columns)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"environment_df is missing required EPS columns: {missing_columns}")
    if environment_df.empty:
        raise ValueError("environment_df must contain at least one row.")


def _as_float_array(frame: pd.DataFrame, column: str) -> NDArray[np.float64]:
    return frame[column].to_numpy(dtype=float)


def _as_bool_array(frame: pd.DataFrame, column: str) -> NDArray[np.bool_]:
    return frame[column].to_numpy(dtype=bool)


def _sun_vectors(environment_df: pd.DataFrame) -> NDArray[np.float64]:
    return environment_df[["sun_hat_x", "sun_hat_y", "sun_hat_z"]].to_numpy(dtype=float)


def _array_normal_vectors(environment_df: pd.DataFrame, config: EpsConfig) -> NDArray[np.float64]:
    normal_columns = ["array_normal_eci_x", "array_normal_eci_y", "array_normal_eci_z"]
    if set(normal_columns).issubset(environment_df.columns):
        normals = environment_df[normal_columns].to_numpy(dtype=float)
    else:
        normal = np.asarray(config.array_normal_eci, dtype=float)
        normals = np.repeat(normal.reshape(1, 3), len(environment_df), axis=0)
    normal_norm = np.linalg.norm(normals, axis=1)
    if np.any(normal_norm == 0.0):
        raise ValueError("Array normal vectors must be non-zero.")
    return normals / normal_norm[:, None]


def _array_incidence_factor(
    environment_df: pd.DataFrame, config: EpsConfig
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    sun_vectors = _sun_vectors(environment_df)
    sun_norm = np.linalg.norm(sun_vectors, axis=1)
    if np.any(sun_norm == 0.0):
        raise ValueError("Sun vectors must be non-zero.")
    sun_hat = sun_vectors / sun_norm[:, None]
    if config.array_pointing_mode == "sun_tracking":
        incidence_factor = np.ones(len(environment_df), dtype=float)
    else:
        array_normal = _array_normal_vectors(environment_df, config)
        incidence_factor = np.clip(np.sum(array_normal * sun_hat, axis=1), 0.0, 1.0)
    return sun_norm, incidence_factor


def _solar_power_w(
    environment_df: pd.DataFrame, config: EpsConfig
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    eclipse = _as_bool_array(environment_df, "eclipse_flag")
    solar_flux_w_m2 = _as_float_array(environment_df, "solar_flux_w_m2")
    sun_norm, incidence_factor = _array_incidence_factor(environment_df, config)

    incidence_factor = np.where(eclipse, 0.0, incidence_factor)
    solar_power_w = (
        solar_flux_w_m2
        * config.array_area_m2
        * config.eta_eol
        * config.sun_pointing_efficiency
        * config.power_conditioning_efficiency
        * incidence_factor
    )
    solar_power_w = np.where(eclipse, 0.0, solar_power_w)
    return solar_power_w, sun_norm, incidence_factor


def _load_schedule_w(
    environment_df: pd.DataFrame, config: EpsConfig
) -> tuple[NDArray[np.float64], NDArray[np.str_], NDArray[np.bool_]]:
    t_s = _as_float_array(environment_df, "t_s")
    eclipse = _as_bool_array(environment_df, "eclipse_flag")
    gs_contact = _as_bool_array(environment_df, "gs_contact_flag")

    base_load_w = np.where(eclipse, config.safe_load_w, config.nominal_load_w)
    cycle_fraction = np.mod(t_s, config.peak_cycle_s) / config.peak_cycle_s
    scheduled_peak = cycle_fraction < config.peak_duty_cycle
    peak_active = np.logical_or(gs_contact, scheduled_peak)

    load_power_w = np.where(peak_active, config.peak_load_w, base_load_w)
    load_mode = np.where(peak_active, "peak", np.where(eclipse, "safe", "nominal"))
    return load_power_w, load_mode, peak_active


def _integrate_battery(
    t_s: NDArray[np.float64],
    solar_power_w: NDArray[np.float64],
    load_power_w: NDArray[np.float64],
    config: EpsConfig,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    if np.any(np.diff(t_s) < 0.0):
        raise ValueError("environment_df t_s values must be monotonically increasing.")

    capacity_j = config.battery_capacity_j
    battery_energy_j = np.empty_like(t_s, dtype=float)
    curtailed_energy_j = np.zeros_like(t_s, dtype=float)
    unserved_energy_j = np.zeros_like(t_s, dtype=float)
    battery_energy_j[0] = capacity_j * config.initial_soc

    for index in range(1, len(t_s)):
        dt_s = t_s[index] - t_s[index - 1]
        average_generation_w = 0.5 * (solar_power_w[index - 1] + solar_power_w[index])
        average_load_w = 0.5 * (load_power_w[index - 1] + load_power_w[index])
        net_power_w = average_generation_w - average_load_w

        if net_power_w >= 0.0:
            delta_energy_j = net_power_w * dt_s * config.charge_efficiency
        else:
            delta_energy_j = net_power_w * dt_s / config.discharge_efficiency

        next_energy_j = battery_energy_j[index - 1] + delta_energy_j
        curtailed_energy_j[index] = curtailed_energy_j[index - 1]
        unserved_energy_j[index] = unserved_energy_j[index - 1]

        if next_energy_j > capacity_j:
            curtailed_energy_j[index] += next_energy_j - capacity_j
            next_energy_j = capacity_j
        elif next_energy_j < 0.0:
            unserved_energy_j[index] += -next_energy_j
            next_energy_j = 0.0

        battery_energy_j[index] = next_energy_j

    return battery_energy_j, curtailed_energy_j, unserved_energy_j


def _integral_j(power_w: NDArray[np.float64], t_s: NDArray[np.float64]) -> float:
    if len(t_s) < 2:
        return 0.0
    return float(np.trapezoid(power_w, t_s))


def _duration_s(flag: NDArray[np.bool_], t_s: NDArray[np.float64]) -> float:
    if len(t_s) < 2:
        return 0.0
    return float(np.sum(np.diff(t_s) * flag[:-1]))


def _time_average_w(power_w: NDArray[np.float64], t_s: NDArray[np.float64]) -> float:
    duration_s = float(t_s[-1] - t_s[0])
    if duration_s <= 0.0:
        return float(power_w[0])
    return _integral_j(power_w, t_s) / duration_s


def _summary(
    timeseries_df: pd.DataFrame,
    config: EpsConfig,
) -> dict[str, float | int]:
    t_s = _as_float_array(timeseries_df, "t_s")
    solar_power_w = _as_float_array(timeseries_df, "solar_power_w")
    load_power_w = _as_float_array(timeseries_df, "load_power_w")
    net_power_w = _as_float_array(timeseries_df, "net_power_w")
    battery_soc = _as_float_array(timeseries_df, "battery_soc")
    eclipse = _as_bool_array(timeseries_df, "eclipse_flag")
    gs_contact = _as_bool_array(timeseries_df, "gs_contact_flag")
    peak_active = _as_bool_array(timeseries_df, "peak_active_flag")

    load_energy_j = _integral_j(load_power_w, t_s)
    generation_energy_j = _integral_j(solar_power_w, t_s)
    battery_swing_j = float(
        timeseries_df["battery_energy_j"].max() - timeseries_df["battery_energy_j"].min()
    )

    return {
        "sample_count": int(len(timeseries_df)),
        "duration_s": float(t_s[-1] - t_s[0]),
        "array_area_m2": config.array_area_m2,
        "eta_eol": config.eta_eol,
        "array_pointing_mode": config.array_pointing_mode,
        "array_eol_power_w": float(
            1361.0
            * config.array_area_m2
            * config.eta_eol
            * config.sun_pointing_efficiency
            * config.power_conditioning_efficiency
        ),
        "battery_capacity_kwh": config.battery_capacity_kwh,
        "battery_capacity_j": config.battery_capacity_j,
        "initial_soc": config.initial_soc,
        "final_soc": float(battery_soc[-1]),
        "min_soc": float(np.min(battery_soc)),
        "max_soc": float(np.max(battery_soc)),
        "max_depth_of_discharge": float(1.0 - np.min(battery_soc)),
        "battery_energy_swing_kwh": battery_swing_j / J_PER_KWH,
        "total_generated_energy_j": generation_energy_j,
        "total_load_energy_j": load_energy_j,
        "net_energy_j": generation_energy_j - load_energy_j,
        "average_generation_w": _time_average_w(solar_power_w, t_s),
        "average_load_w": _time_average_w(load_power_w, t_s),
        "peak_generated_power_w": float(np.max(solar_power_w)),
        "peak_load_w": float(np.max(load_power_w)),
        "minimum_array_incidence_factor": float(np.min(timeseries_df["array_incidence_factor"])),
        "average_array_incidence_factor": _time_average_w(
            _as_float_array(timeseries_df, "array_incidence_factor"), t_s
        ),
        "min_power_margin_w": float(np.min(net_power_w)),
        "eclipse_duration_s": _duration_s(eclipse, t_s),
        "sunlight_duration_s": float(t_s[-1] - t_s[0]) - _duration_s(eclipse, t_s),
        "ground_contact_duration_s": _duration_s(gs_contact, t_s),
        "peak_load_duration_s": _duration_s(peak_active, t_s),
        "curtailed_energy_j": float(timeseries_df["curtailed_energy_j"].iloc[-1]),
        "unserved_energy_j": float(timeseries_df["unserved_energy_j"].iloc[-1]),
    }


def run_eps(
    environment_df: pd.DataFrame, config: EpsConfig | None = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Run the LunaLink EPS model against a Phase 2 environment table.

    Parameters
    ----------
    environment_df:
        DataFrame from :func:`lunalink.environment.build_environment_table`.
    config:
        Optional EPS sizing and load configuration. Defaults are representative
        planning values for a small communications spacecraft.
    """

    eps_config = config or EpsConfig()
    _require_environment_columns(environment_df)

    timeseries_df = environment_df.reset_index(drop=True).copy()
    t_s = _as_float_array(timeseries_df, "t_s")
    solar_power_w, sun_norm, incidence_factor = _solar_power_w(timeseries_df, eps_config)
    load_power_w, load_mode, peak_active = _load_schedule_w(timeseries_df, eps_config)
    net_power_w = solar_power_w - load_power_w
    battery_energy_j, curtailed_energy_j, unserved_energy_j = _integrate_battery(
        t_s, solar_power_w, load_power_w, eps_config
    )

    timeseries_df["sun_vector_norm"] = sun_norm
    timeseries_df["array_incidence_factor"] = incidence_factor
    timeseries_df["solar_power_w"] = solar_power_w
    timeseries_df["load_power_w"] = load_power_w
    timeseries_df["load_mode"] = load_mode
    timeseries_df["peak_active_flag"] = peak_active
    timeseries_df["net_power_w"] = net_power_w
    timeseries_df["battery_energy_j"] = battery_energy_j
    timeseries_df["battery_soc"] = battery_energy_j / eps_config.battery_capacity_j
    timeseries_df["curtailed_energy_j"] = curtailed_energy_j
    timeseries_df["unserved_energy_j"] = unserved_energy_j

    return timeseries_df, _summary(timeseries_df, eps_config)
