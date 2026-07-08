"""TT&C/RF link-budget utilities for LunaLink."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from typing import Any

import numpy as np
import pandas as pd

from .constants import SPEED_OF_LIGHT_M_S

BOLTZMANN_W_HZ_K = 1.380649e-23
DEFAULT_MIN_ELEVATION_RAD = math.radians(5.0)


@dataclass(frozen=True)
class LinkConfig:
    """Single RF link configuration in SI units and dB losses."""

    name: str
    frequency_hz: float
    data_rate_bps: float
    tx_power_w: float
    system_noise_temp_k: float
    required_ebn0_db: float
    margin_threshold_db: float = 3.0
    tx_gain_dbi: float | None = None
    rx_gain_dbi: float | None = None
    tx_antenna_diameter_m: float | None = None
    tx_antenna_efficiency: float = 1.0
    rx_antenna_diameter_m: float | None = None
    rx_antenna_efficiency: float = 1.0
    tx_line_loss_db: float = 0.0
    rx_line_loss_db: float = 0.0
    propagation_loss_db: float = 0.0
    implementation_loss_db: float = 0.0

    def __post_init__(self) -> None:
        for name in ("frequency_hz", "data_rate_bps", "tx_power_w", "system_noise_temp_k"):
            _positive_float(getattr(self, name), name)
        for name in ("tx_antenna_efficiency", "rx_antenna_efficiency"):
            _efficiency_float(getattr(self, name), name)
        for name in (
            "tx_line_loss_db",
            "rx_line_loss_db",
            "propagation_loss_db",
            "implementation_loss_db",
            "margin_threshold_db",
        ):
            _nonnegative_float(getattr(self, name), name)
        for name in ("required_ebn0_db", "tx_gain_dbi", "rx_gain_dbi"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(float(value)):
                raise ValueError(f"{name} must be finite when provided")

    def resolved_tx_gain_dbi(self) -> float:
        return _resolve_gain_dbi(
            explicit_gain_dbi=self.tx_gain_dbi,
            diameter_m=self.tx_antenna_diameter_m,
            efficiency=self.tx_antenna_efficiency,
            frequency_hz=self.frequency_hz,
            label="tx",
        )

    def resolved_rx_gain_dbi(self) -> float:
        return _resolve_gain_dbi(
            explicit_gain_dbi=self.rx_gain_dbi,
            diameter_m=self.rx_antenna_diameter_m,
            efficiency=self.rx_antenna_efficiency,
            frequency_hz=self.frequency_hz,
            label="rx",
        )


def default_xband_link_config() -> LinkConfig:
    """Return the baseline Earth X-band downlink configuration."""

    return LinkConfig(
        name="xband",
        frequency_hz=8.4e9,
        data_rate_bps=100.0e6,
        tx_power_w=20.0,
        tx_antenna_diameter_m=0.6,
        tx_antenna_efficiency=0.60,
        rx_antenna_diameter_m=3.0,
        rx_antenna_efficiency=0.62,
        system_noise_temp_k=150.0,
        required_ebn0_db=5.0,
        margin_threshold_db=3.0,
        propagation_loss_db=1.5 + 0.5 + 1.2,
        implementation_loss_db=2.0,
    )


def default_uhf_link_config() -> LinkConfig:
    """Return the baseline Moon UHF low-rate link configuration."""

    return LinkConfig(
        name="uhf",
        frequency_hz=450.0e6,
        data_rate_bps=10.0e3,
        tx_power_w=25.0,
        tx_gain_dbi=20.0,
        rx_gain_dbi=18.0,
        system_noise_temp_k=500.0,
        required_ebn0_db=6.0,
        margin_threshold_db=3.0,
        propagation_loss_db=0.5 + 2.0,
        implementation_loss_db=2.0,
    )


@dataclass(frozen=True)
class TtcConfig:
    """TT&C defaults for the Earth downlink and Moon UHF link."""

    xband: LinkConfig = field(default_factory=default_xband_link_config)
    uhf: LinkConfig = field(default_factory=default_uhf_link_config)
    ground_min_elevation_rad: float = DEFAULT_MIN_ELEVATION_RAD

    def __post_init__(self) -> None:
        if not math.isfinite(float(self.ground_min_elevation_rad)):
            raise ValueError("ground_min_elevation_rad must be finite")


def antenna_gain_dbi(frequency_hz: float, diameter_m: float, efficiency: float = 1.0) -> float:
    """Return parabolic antenna gain in dBi from frequency, diameter, and efficiency."""

    frequency_hz = _positive_float(frequency_hz, "frequency_hz")
    diameter_m = _positive_float(diameter_m, "diameter_m")
    efficiency = _efficiency_float(efficiency, "efficiency")
    wavelength_m = SPEED_OF_LIGHT_M_S / frequency_hz
    gain_linear = efficiency * (math.pi * diameter_m / wavelength_m) ** 2
    return 10.0 * math.log10(gain_linear)


def free_space_path_loss_db(range_m: float, frequency_hz: float) -> float:
    """Return free-space path loss in dB for range in meters and frequency in Hz."""

    range_m = _positive_float(range_m, "range_m")
    frequency_hz = _positive_float(frequency_hz, "frequency_hz")
    wavelength_m = SPEED_OF_LIGHT_M_S / frequency_hz
    return 20.0 * math.log10(4.0 * math.pi * range_m / wavelength_m)


def link_budget(
    range_m: float,
    frequency_hz: float,
    data_rate_bps: float,
    tx_power_w: float,
    tx_gain_dbi: float,
    rx_gain_dbi: float,
    system_noise_temp_k: float,
    required_ebn0_db: float,
    margin_threshold_db: float = 3.0,
    tx_line_loss_db: float = 0.0,
    rx_line_loss_db: float = 0.0,
    propagation_loss_db: float = 0.0,
    implementation_loss_db: float = 0.0,
) -> dict[str, float | bool]:
    """Compute a deterministic SI/dB link budget for a single range sample."""

    range_m = _positive_float(range_m, "range_m")
    frequency_hz = _positive_float(frequency_hz, "frequency_hz")
    data_rate_bps = _positive_float(data_rate_bps, "data_rate_bps")
    tx_power_w = _positive_float(tx_power_w, "tx_power_w")
    system_noise_temp_k = _positive_float(system_noise_temp_k, "system_noise_temp_k")

    tx_power_dbw = 10.0 * math.log10(tx_power_w)
    fspl_db = free_space_path_loss_db(range_m, frequency_hz)
    eirp_dbw = tx_power_dbw + tx_gain_dbi - tx_line_loss_db
    g_over_t_db_per_k = rx_gain_dbi - rx_line_loss_db - 10.0 * math.log10(
        system_noise_temp_k
    )
    carrier_power_dbw = (
        eirp_dbw + rx_gain_dbi - rx_line_loss_db - fspl_db - propagation_loss_db
    )
    noise_density_dbw_hz = 10.0 * math.log10(BOLTZMANN_W_HZ_K * system_noise_temp_k)
    cn0_db_hz = carrier_power_dbw - noise_density_dbw_hz
    ebn0_db = cn0_db_hz - 10.0 * math.log10(data_rate_bps) - implementation_loss_db
    margin_db = ebn0_db - required_ebn0_db

    return {
        "range_m": range_m,
        "frequency_hz": frequency_hz,
        "data_rate_bps": data_rate_bps,
        "tx_power_dbw": tx_power_dbw,
        "tx_gain_dbi": float(tx_gain_dbi),
        "rx_gain_dbi": float(rx_gain_dbi),
        "eirp_dbw": eirp_dbw,
        "g_over_t_db_per_k": g_over_t_db_per_k,
        "fspl_db": fspl_db,
        "path_loss_db": fspl_db,
        "propagation_loss_db": float(propagation_loss_db),
        "implementation_loss_db": float(implementation_loss_db),
        "carrier_power_dbw": carrier_power_dbw,
        "noise_density_dbw_hz": noise_density_dbw_hz,
        "cn0_db_hz": cn0_db_hz,
        "ebn0_db": ebn0_db,
        "required_ebn0_db": float(required_ebn0_db),
        "margin_db": margin_db,
        "margin_threshold_db": float(margin_threshold_db),
        "available_flag": bool(margin_db >= margin_threshold_db),
    }


def contact_windows(times_s: Any, contact_flags: Any) -> list[dict[str, float]]:
    """Convert sampled contact flags into start/end/duration windows."""

    times = _as_float_array(times_s, "times_s")
    flags = _as_bool_array(contact_flags, "contact_flags")
    _validate_time_and_flag_arrays(times, flags)

    windows: list[dict[str, float]] = []
    start_s: float | None = None
    for time_s, flag in zip(times, flags, strict=True):
        if flag and start_s is None:
            start_s = float(time_s)
        elif not flag and start_s is not None:
            end_s = float(time_s)
            windows.append(
                {"start_s": start_s, "end_s": end_s, "duration_s": end_s - start_s}
            )
            start_s = None

    if start_s is not None:
        end_s = float(times[-1])
        windows.append({"start_s": start_s, "end_s": end_s, "duration_s": end_s - start_s})

    return windows


def threshold_windows(
    times_s: Any,
    values: Any,
    threshold: float,
) -> list[dict[str, float]]:
    """Return linearly interpolated windows where ``values >= threshold``."""

    times = _as_float_array(times_s, "times_s")
    samples = _as_float_array(values, "values")
    if len(times) != len(samples):
        raise ValueError("times_s and values must have equal length")
    _validate_times(times)
    if len(times) == 0:
        return []

    flags = samples >= float(threshold)
    windows: list[dict[str, float]] = []
    start_s: float | None = float(times[0]) if flags[0] else None
    for index in range(len(times) - 1):
        if flags[index] == flags[index + 1]:
            continue
        crossing_s = _linear_crossing_time(
            times[index],
            times[index + 1],
            samples[index],
            samples[index + 1],
            float(threshold),
        )
        if not flags[index] and flags[index + 1]:
            start_s = crossing_s
        elif flags[index] and not flags[index + 1] and start_s is not None:
            windows.append(
                {"start_s": start_s, "end_s": crossing_s, "duration_s": crossing_s - start_s}
            )
            start_s = None
    if start_s is not None:
        windows.append(
            {
                "start_s": start_s,
                "end_s": float(times[-1]),
                "duration_s": float(times[-1]) - start_s,
            }
        )
    return windows


def _linear_crossing_time(
    t0_s: float,
    t1_s: float,
    value0: float,
    value1: float,
    threshold: float,
) -> float:
    if value1 == value0:
        return float(t1_s)
    fraction = (threshold - value0) / (value1 - value0)
    fraction = min(1.0, max(0.0, float(fraction)))
    return float(t0_s + fraction * (t1_s - t0_s))


def run_ttc(
    environment_df: pd.DataFrame, config: Any = None
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Evaluate Earth X-band and Moon UHF TT&C links from the shared environment table."""

    required_columns = {
        "t_s",
        "gs_range_m",
        "gs_elevation_rad",
        "gs_contact_flag",
        "moon_range_m",
        "moon_occulted_flag",
    }
    missing = required_columns.difference(environment_df.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise KeyError(f"environment_df missing required TT&C columns: {missing_text}")

    cfg = _coerce_ttc_config(config)
    times = _as_float_array(environment_df["t_s"], "t_s")
    _validate_times(times)
    durations_s = _sample_durations_s(times)

    base = environment_df[
        [
            "t_s",
            "gs_range_m",
            "gs_elevation_rad",
            "gs_contact_flag",
            "moon_range_m",
            "moon_occulted_flag",
        ]
    ].reset_index(drop=True)

    xband = _evaluate_link(
        prefix="xband",
        ranges_m=base["gs_range_m"],
        geometry_flags=base["gs_contact_flag"],
        durations_s=durations_s,
        link=cfg.xband,
    )
    uhf = _evaluate_link(
        prefix="uhf",
        ranges_m=base["moon_range_m"],
        geometry_flags=~base["moon_occulted_flag"].astype(bool),
        durations_s=durations_s,
        link=cfg.uhf,
    )

    timeseries = pd.concat([base, xband, uhf], axis=1)
    summary = _build_summary(times, timeseries, cfg)
    return timeseries, summary


def _evaluate_link(
    prefix: str,
    ranges_m: Any,
    geometry_flags: Any,
    durations_s: np.ndarray,
    link: LinkConfig,
) -> pd.DataFrame:
    range_values = _as_float_array(ranges_m, f"{prefix}_range_m")
    geometry = _as_bool_array(geometry_flags, f"{prefix}_geometry_flags")
    if len(range_values) != len(durations_s):
        raise ValueError(f"{prefix} ranges and durations must have equal length")
    if len(geometry) != len(durations_s):
        raise ValueError(f"{prefix} geometry flags and durations must have equal length")

    tx_gain_dbi = link.resolved_tx_gain_dbi()
    rx_gain_dbi = link.resolved_rx_gain_dbi()
    budgets = [
        link_budget(
            range_m=range_m,
            frequency_hz=link.frequency_hz,
            data_rate_bps=link.data_rate_bps,
            tx_power_w=link.tx_power_w,
            tx_gain_dbi=tx_gain_dbi,
            rx_gain_dbi=rx_gain_dbi,
            system_noise_temp_k=link.system_noise_temp_k,
            required_ebn0_db=link.required_ebn0_db,
            margin_threshold_db=link.margin_threshold_db,
            tx_line_loss_db=link.tx_line_loss_db,
            rx_line_loss_db=link.rx_line_loss_db,
            propagation_loss_db=link.propagation_loss_db,
            implementation_loss_db=link.implementation_loss_db,
        )
        for range_m in range_values
    ]

    margin_ok = np.array([bool(budget["available_flag"]) for budget in budgets], dtype=bool)
    available = geometry & margin_ok
    active_rate_bps = np.where(available, link.data_rate_bps, 0.0)
    volume_bits = active_rate_bps * durations_s

    return pd.DataFrame(
        {
            f"{prefix}_range_m": range_values,
            f"{prefix}_frequency_hz": link.frequency_hz,
            f"{prefix}_data_rate_bps": link.data_rate_bps,
            f"{prefix}_tx_power_w": link.tx_power_w,
            f"{prefix}_tx_gain_dbi": tx_gain_dbi,
            f"{prefix}_rx_gain_dbi": rx_gain_dbi,
            f"{prefix}_eirp_dbw": [budget["eirp_dbw"] for budget in budgets],
            f"{prefix}_g_over_t_db_per_k": [budget["g_over_t_db_per_k"] for budget in budgets],
            f"{prefix}_fspl_db": [budget["fspl_db"] for budget in budgets],
            f"{prefix}_propagation_loss_db": link.propagation_loss_db,
            f"{prefix}_implementation_loss_db": link.implementation_loss_db,
            f"{prefix}_carrier_power_dbw": [budget["carrier_power_dbw"] for budget in budgets],
            f"{prefix}_noise_density_dbw_hz": [
                budget["noise_density_dbw_hz"] for budget in budgets
            ],
            f"{prefix}_cn0_db_hz": [budget["cn0_db_hz"] for budget in budgets],
            f"{prefix}_ebn0_db": [budget["ebn0_db"] for budget in budgets],
            f"{prefix}_required_ebn0_db": link.required_ebn0_db,
            f"{prefix}_margin_db": [budget["margin_db"] for budget in budgets],
            f"{prefix}_margin_threshold_db": link.margin_threshold_db,
            f"{prefix}_geometry_flag": geometry,
            f"{prefix}_margin_ok_flag": margin_ok,
            f"{prefix}_available_flag": available,
            f"{prefix}_active_rate_bps": active_rate_bps,
            f"{prefix}_volume_bits": volume_bits,
            f"{prefix}_cumulative_volume_bits": np.cumsum(volume_bits),
        }
    )


def _build_summary(
    times_s: np.ndarray, timeseries: pd.DataFrame, config: TtcConfig
) -> dict[str, Any]:
    xband_available = timeseries["xband_available_flag"].to_numpy(dtype=bool)
    xband_geometry = timeseries["xband_geometry_flag"].to_numpy(dtype=bool)
    uhf_available = timeseries["uhf_available_flag"].to_numpy(dtype=bool)
    uhf_geometry = timeseries["uhf_geometry_flag"].to_numpy(dtype=bool)

    xband_volume = _last_or_zero(timeseries["xband_cumulative_volume_bits"])
    uhf_volume = _last_or_zero(timeseries["uhf_cumulative_volume_bits"])

    return {
        "xband_contact_windows": contact_windows(times_s, xband_geometry),
        "xband_refined_contact_windows": threshold_windows(
            times_s,
            timeseries["gs_elevation_rad"],
            config.ground_min_elevation_rad,
        ),
        "xband_available_windows": contact_windows(times_s, xband_available),
        "xband_contact_duration_s": _flag_duration_s(times_s, xband_geometry),
        "xband_available_duration_s": _flag_duration_s(times_s, xband_available),
        "xband_data_volume_bits": xband_volume,
        "xband_min_margin_db": _masked_min(timeseries["xband_margin_db"], xband_geometry),
        "xband_max_margin_db": _masked_max(timeseries["xband_margin_db"], xband_geometry),
        "xband_data_rate_bps": config.xband.data_rate_bps,
        "uhf_visibility_windows": contact_windows(times_s, uhf_geometry),
        "uhf_available_windows": contact_windows(times_s, uhf_available),
        "uhf_visibility_duration_s": _flag_duration_s(times_s, uhf_geometry),
        "uhf_available_duration_s": _flag_duration_s(times_s, uhf_available),
        "uhf_data_volume_bits": uhf_volume,
        "uhf_min_margin_db": _masked_min(timeseries["uhf_margin_db"], uhf_geometry),
        "uhf_max_margin_db": _masked_max(timeseries["uhf_margin_db"], uhf_geometry),
        "uhf_data_rate_bps": config.uhf.data_rate_bps,
        "aggregate_independent_link_volume_bits": xband_volume + uhf_volume,
        "end_to_end_relay_volume_bits": min(xband_volume, uhf_volume),
        "total_data_volume_bits": xband_volume + uhf_volume,
        "data_volume_note": (
            "Total is aggregate independent link volume; end-to-end relay is min(UHF, X-band)."
        ),
        "xband_window_model": "Sampled flags plus linearly interpolated 5 deg elevation crossings.",
        "uhf_geometry_model": "Moon-center range with Earth occultation screening only.",
    }


def _coerce_ttc_config(config: Any) -> TtcConfig:
    if config is None:
        return TtcConfig()
    if isinstance(config, TtcConfig):
        return config
    if isinstance(config, Mapping):
        return _ttc_config_from_mapping(config)

    nested = getattr(config, "ttc", None)
    if nested is None:
        return TtcConfig()
    return _coerce_ttc_config(nested)


def _ttc_config_from_mapping(values: Mapping[str, Any]) -> TtcConfig:
    xband_values = values.get("xband", values.get("xband_downlink", {}))
    uhf_values = values.get("uhf", values.get("moon_uhf", {}))
    if not isinstance(xband_values, Mapping) or not isinstance(uhf_values, Mapping):
        raise TypeError("xband and uhf config overrides must be mappings")
    return TtcConfig(
        xband=_replace_link_config(default_xband_link_config(), xband_values),
        uhf=_replace_link_config(default_uhf_link_config(), uhf_values),
        ground_min_elevation_rad=float(
            values.get("ground_min_elevation_rad", DEFAULT_MIN_ELEVATION_RAD)
        ),
    )


def _replace_link_config(base: LinkConfig, values: Mapping[str, Any]) -> LinkConfig:
    allowed = {field_info.name for field_info in fields(LinkConfig)}
    unknown = set(values).difference(allowed)
    if unknown:
        unknown_text = ", ".join(sorted(unknown))
        raise KeyError(f"unknown LinkConfig override keys: {unknown_text}")
    return replace(base, **dict(values))


def _resolve_gain_dbi(
    explicit_gain_dbi: float | None,
    diameter_m: float | None,
    efficiency: float,
    frequency_hz: float,
    label: str,
) -> float:
    if explicit_gain_dbi is not None:
        return float(explicit_gain_dbi)
    if diameter_m is None:
        raise ValueError(f"{label} gain requires either explicit gain_dbi or antenna diameter")
    return antenna_gain_dbi(frequency_hz, diameter_m, efficiency)


def _positive_float(value: Any, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be a finite positive value")
    return value


def _nonnegative_float(value: Any, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return value


def _efficiency_float(value: Any, name: str) -> float:
    value = _positive_float(value, name)
    if value > 1.0:
        raise ValueError(f"{name} must be less than or equal to 1")
    return value


def _as_float_array(values: Any, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} must contain finite values")
    return array


def _as_bool_array(values: Any, name: str) -> np.ndarray:
    array = np.asarray(values, dtype=bool)
    if array.ndim != 1:
        raise ValueError(f"{name} must be one-dimensional")
    return array


def _validate_time_and_flag_arrays(times_s: np.ndarray, flags: np.ndarray) -> None:
    if len(times_s) != len(flags):
        raise ValueError("times_s and contact_flags must have equal length")
    _validate_times(times_s)


def _validate_times(times_s: np.ndarray) -> None:
    if len(times_s) == 0:
        return
    if np.any(np.diff(times_s) < 0.0):
        raise ValueError("times must be monotonically nondecreasing")


def _sample_durations_s(times_s: np.ndarray) -> np.ndarray:
    if len(times_s) == 0:
        return np.array([], dtype=float)
    return np.diff(times_s, append=times_s[-1])


def _flag_duration_s(times_s: np.ndarray, flags: np.ndarray) -> float:
    return float(np.sum(_sample_durations_s(times_s) * flags.astype(float)))


def _last_or_zero(values: pd.Series) -> float:
    if len(values) == 0:
        return 0.0
    return float(values.iloc[-1])


def _masked_min(values: pd.Series, mask: np.ndarray) -> float | None:
    selected = values.to_numpy(dtype=float)[mask]
    if len(selected) == 0:
        return None
    return float(np.min(selected))


def _masked_max(values: pd.Series, mask: np.ndarray) -> float | None:
    selected = values.to_numpy(dtype=float)[mask]
    if len(selected) == 0:
        return None
    return float(np.max(selected))
