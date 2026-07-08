"""Simple seven-node spacecraft thermal model."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

import numpy as np
import pandas as pd

from .constants import STEFAN_BOLTZMANN_W_M2_K4

FACE_NAMES: tuple[str, ...] = ("x_pos", "x_neg", "y_pos", "y_neg", "z_pos", "z_neg")


@dataclass(frozen=True)
class Coating:
    """External optical properties for a simplified spacecraft surface."""

    solar_absorptivity: float
    ir_emissivity: float


COATING_TABLE: Mapping[str, Coating] = MappingProxyType(
    {
        "white": Coating(solar_absorptivity=0.25, ir_emissivity=0.85),
        "black": Coating(solar_absorptivity=0.90, ir_emissivity=0.90),
        "OSR/FEP": Coating(solar_absorptivity=0.14, ir_emissivity=0.82),
        "MLI": Coating(solar_absorptivity=0.12, ir_emissivity=0.035),
    }
)


def box_face_areas_m2(
    length_x_m: float = 2.0, length_y_m: float = 1.5, length_z_m: float = 1.0
) -> dict[str, float]:
    """Return areas for the six faces of a rectangular spacecraft bus."""

    return {
        "x_pos": length_y_m * length_z_m,
        "x_neg": length_y_m * length_z_m,
        "y_pos": length_x_m * length_z_m,
        "y_neg": length_x_m * length_z_m,
        "z_pos": length_x_m * length_y_m,
        "z_neg": length_x_m * length_y_m,
    }


FACE_AREAS_M2: Mapping[str, float] = MappingProxyType(box_face_areas_m2())
DEFAULT_FACE_AREAS_M2 = FACE_AREAS_M2

SOLAR_VIEW_FACTORS: Mapping[str, float] = MappingProxyType(
    {
        "x_pos": 1.00,
        "x_neg": 0.00,
        "y_pos": 0.15,
        "y_neg": 0.15,
        "z_pos": 0.10,
        "z_neg": 0.00,
    }
)
EARTH_VIEW_FACTORS: Mapping[str, float] = MappingProxyType(
    {
        "x_pos": 0.25,
        "x_neg": 0.25,
        "y_pos": 0.25,
        "y_neg": 0.25,
        "z_pos": 0.05,
        "z_neg": 1.00,
    }
)

REQUIRED_ENVIRONMENT_COLUMNS: tuple[str, ...] = (
    "t_s",
    "eclipse_flag",
    "solar_flux_w_m2",
    "earth_ir_flux_w_m2",
    "albedo_flux_w_m2",
)


@dataclass(frozen=True)
class ThermalConfig:
    """Configuration for the LunaLink seven-node thermal approximation."""

    coating: str = "white"
    face_coatings: Mapping[str, str] | None = None
    length_x_m: float = 2.0
    length_y_m: float = 1.5
    length_z_m: float = 1.0
    initial_temp_k: float = 293.15
    default_internal_power_w: float = 120.0
    internal_heat_capacity_j_k: float = 120_000.0
    face_heat_capacity_j_m2_k: float = 3_000.0
    internal_conductance_w_m2_k: float = 6.0
    max_step_s: float = 10.0
    min_physical_temp_k: float = 1.0
    deep_space_temp_k: float = 3.0
    internal_min_operating_k: float = 263.15
    internal_max_operating_k: float = 323.15
    external_min_operating_k: float = 173.15
    external_max_operating_k: float = 373.15


def _coating_for(name: str) -> tuple[str, Coating]:
    normalized = name.strip().lower().replace("_", "/")
    aliases = {
        "white": "white",
        "black": "black",
        "osr": "OSR/FEP",
        "fep": "OSR/FEP",
        "osr/fep": "OSR/FEP",
        "mli": "MLI",
    }
    try:
        canonical = aliases[normalized]
    except KeyError as exc:
        allowed = ", ".join(COATING_TABLE)
        raise ValueError(f"Unknown coating {name!r}; expected one of: {allowed}.") from exc
    return canonical, COATING_TABLE[canonical]


def default_face_coatings() -> dict[str, str]:
    """Return a mixed passive-control coating layout for the baseline bus."""

    return {
        "x_pos": "white",
        "x_neg": "MLI",
        "y_pos": "white",
        "y_neg": "MLI",
        "z_pos": "MLI",
        "z_neg": "OSR/FEP",
    }


def _face_coatings(config: ThermalConfig) -> tuple[list[str], list[Coating]]:
    names: list[str] = []
    coatings: list[Coating] = []
    overrides = config.face_coatings or {}
    for face in FACE_NAMES:
        canonical, coating = _coating_for(overrides.get(face, config.coating))
        names.append(canonical)
        coatings.append(coating)
    return names, coatings


def _validated_environment(environment_df: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED_ENVIRONMENT_COLUMNS) - set(environment_df.columns))
    if missing:
        raise ValueError(f"Environment table missing required columns: {', '.join(missing)}")
    if environment_df.empty:
        raise ValueError("Environment table must contain at least one row.")

    env = environment_df.copy()
    env = env.sort_values("t_s", kind="mergesort").reset_index(drop=True)
    if env["t_s"].isna().any():
        raise ValueError("Environment time column contains NaN values.")
    if env["t_s"].diff().dropna().lt(0.0).any():
        raise ValueError("Environment time column must be monotonically increasing.")
    return env


def _validate_config(config: ThermalConfig) -> None:
    if config.initial_temp_k <= 0.0:
        raise ValueError("Initial temperature must be positive Kelvin.")
    if config.max_step_s <= 0.0:
        raise ValueError("Thermal integration max_step_s must be positive.")
    if config.internal_heat_capacity_j_k <= 0.0 or config.face_heat_capacity_j_m2_k <= 0.0:
        raise ValueError("Thermal heat capacities must be positive.")
    if config.internal_conductance_w_m2_k < 0.0:
        raise ValueError("Internal conductance cannot be negative.")
    if config.min_physical_temp_k <= 0.0:
        raise ValueError("Minimum physical temperature clamp must be positive Kelvin.")


def _environment_fluxes(row: pd.Series) -> tuple[float, float, float]:
    solar_flux = float(row.solar_flux_w_m2)
    if bool(row.eclipse_flag):
        solar_flux = 0.0
    return (
        max(0.0, solar_flux),
        max(0.0, float(row.earth_ir_flux_w_m2)),
        max(0.0, float(row.albedo_flux_w_m2)),
    )


def _power_profile_w(
    env: pd.DataFrame,
    power_w: float | Sequence[float] | pd.Series | None,
    config: ThermalConfig,
) -> np.ndarray:
    if power_w is None:
        return np.full(len(env), config.default_internal_power_w, dtype=float)
    if np.isscalar(power_w):
        return np.full(len(env), float(power_w), dtype=float)
    values = np.asarray(power_w, dtype=float)
    if values.ndim != 1 or len(values) != len(env):
        raise ValueError("Thermal power profile must match the environment table length.")
    if not np.isfinite(values).all():
        raise ValueError("Thermal power profile must contain finite values.")
    return values


def _unit_or_none(vector: np.ndarray) -> np.ndarray | None:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return None
    return vector / norm


def _dynamic_view_factors(row: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    """Estimate face view factors for a nominal LVLH/nadir-pointing bus."""

    required = {
        "x_eci_m",
        "y_eci_m",
        "z_eci_m",
        "vx_eci_mps",
        "vy_eci_mps",
        "vz_eci_mps",
        "sun_hat_x",
        "sun_hat_y",
        "sun_hat_z",
    }
    if not required.issubset(row.index):
        return (
            np.array([SOLAR_VIEW_FACTORS[face] for face in FACE_NAMES], dtype=float),
            np.array([EARTH_VIEW_FACTORS[face] for face in FACE_NAMES], dtype=float),
        )

    r_eci = np.array([row.x_eci_m, row.y_eci_m, row.z_eci_m], dtype=float)
    v_eci = np.array([row.vx_eci_mps, row.vy_eci_mps, row.vz_eci_mps], dtype=float)
    sun_hat = _unit_or_none(np.array([row.sun_hat_x, row.sun_hat_y, row.sun_hat_z], dtype=float))
    radial_hat = _unit_or_none(r_eci)
    if sun_hat is None or radial_hat is None:
        return (
            np.array([SOLAR_VIEW_FACTORS[face] for face in FACE_NAMES], dtype=float),
            np.array([EARTH_VIEW_FACTORS[face] for face in FACE_NAMES], dtype=float),
        )

    along_track = v_eci - np.dot(v_eci, radial_hat) * radial_hat
    x_pos = _unit_or_none(along_track)
    if x_pos is None:
        x_pos = np.array([1.0, 0.0, 0.0], dtype=float)
    y_pos = _unit_or_none(np.cross(radial_hat, x_pos))
    if y_pos is None:
        y_pos = np.array([0.0, 1.0, 0.0], dtype=float)

    normals = {
        "x_pos": x_pos,
        "x_neg": -x_pos,
        "y_pos": y_pos,
        "y_neg": -y_pos,
        "z_pos": radial_hat,
        "z_neg": -radial_hat,
    }
    nadir_hat = -radial_hat
    solar_view = np.array([max(0.0, float(np.dot(normals[face], sun_hat))) for face in FACE_NAMES])
    earth_view = np.array(
        [max(0.0, float(np.dot(normals[face], nadir_hat))) for face in FACE_NAMES]
    )
    return solar_view, earth_view


def run_thermal(
    environment_df: pd.DataFrame,
    power_w: float | Sequence[float] | pd.Series | None = None,
    config: ThermalConfig | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    """Propagate a seven-node thermal model over an environment table.

    The model contains six external face nodes and one internal equipment node.
    Solar and albedo fluxes use solar absorptivity; Earth IR and emitted
    radiation use IR emissivity. Internal heat leaves the equipment node through
    area-scaled conductive links to the external faces. Face view factors assume
    a nominal LVLH/nadir-pointing bus and are not coupled to the ADCS quaternion
    history in this preliminary baseline.
    """

    thermal_config = config or ThermalConfig()
    _validate_config(thermal_config)
    env = _validated_environment(environment_df)
    power_profile = _power_profile_w(env, power_w, thermal_config)
    coating_names, coatings = _face_coatings(thermal_config)
    solar_absorptivity = np.array([coating.solar_absorptivity for coating in coatings], dtype=float)
    ir_emissivity = np.array([coating.ir_emissivity for coating in coatings], dtype=float)
    canonical_coating = coating_names[0] if len(set(coating_names)) == 1 else "mixed"

    face_areas = box_face_areas_m2(
        thermal_config.length_x_m, thermal_config.length_y_m, thermal_config.length_z_m
    )
    area = np.array([face_areas[face] for face in FACE_NAMES], dtype=float)
    face_heat_capacity = area * thermal_config.face_heat_capacity_j_m2_k
    conductance = area * thermal_config.internal_conductance_w_m2_k

    face_temp_k = np.full(len(FACE_NAMES), thermal_config.initial_temp_k, dtype=float)
    internal_temp_k = float(thermal_config.initial_temp_k)
    min_temp_k = thermal_config.min_physical_temp_k
    deep_space_temp_k4 = thermal_config.deep_space_temp_k**4
    rows: list[dict[str, float | bool | str]] = []

    def record(
        t_s: float, power_sample_w: float, solar_view: np.ndarray, earth_view: np.ndarray
    ) -> None:
        row: dict[str, float | bool | str] = {
            "t_s": float(t_s),
            "coating": canonical_coating,
            "power_w": float(power_sample_w),
            "mean_solar_view_factor": float(np.mean(solar_view)),
            "mean_earth_view_factor": float(np.mean(earth_view)),
            "temp_internal_k": float(internal_temp_k),
            "temp_internal_c": float(internal_temp_k - 273.15),
            "temp_min_k": float(min(np.min(face_temp_k), internal_temp_k)),
            "temp_max_k": float(max(np.max(face_temp_k), internal_temp_k)),
            "internal_cold_limit_flag": bool(
                internal_temp_k < thermal_config.internal_min_operating_k
            ),
            "internal_hot_limit_flag": bool(
                internal_temp_k > thermal_config.internal_max_operating_k
            ),
            "external_cold_limit_flag": bool(
                np.any(face_temp_k < thermal_config.external_min_operating_k)
            ),
            "external_hot_limit_flag": bool(
                np.any(face_temp_k > thermal_config.external_max_operating_k)
            ),
        }
        for face, temperature, coating_name, solar_factor, earth_factor in zip(
            FACE_NAMES, face_temp_k, coating_names, solar_view, earth_view, strict=True
        ):
            row[f"coating_{face}"] = coating_name
            row[f"solar_view_{face}"] = float(solar_factor)
            row[f"earth_view_{face}"] = float(earth_factor)
            row[f"temp_{face}_k"] = float(temperature)
            row[f"temp_{face}_c"] = float(temperature - 273.15)
        row["component_limit_flag"] = bool(
            row["internal_cold_limit_flag"]
            or row["internal_hot_limit_flag"]
            or row["external_cold_limit_flag"]
            or row["external_hot_limit_flag"]
        )
        rows.append(row)

    initial_solar_view, initial_earth_view = _dynamic_view_factors(env.iloc[0])
    record(float(env.iloc[0].t_s), float(power_profile[0]), initial_solar_view, initial_earth_view)

    for index in range(1, len(env)):
        previous = env.iloc[index - 1]
        target_t_s = float(env.iloc[index].t_s)
        remaining_s = target_t_s - float(previous.t_s)
        if remaining_s < 0.0:
            raise ValueError("Environment time column must be monotonically increasing.")

        solar_flux, earth_ir_flux, albedo_flux = _environment_fluxes(previous)
        solar_view, earth_view = _dynamic_view_factors(previous)
        interval_power_w = float(power_profile[index - 1])
        absorbed_w = area * (
            solar_absorptivity * (solar_flux * solar_view + albedo_flux * earth_view)
            + ir_emissivity * earth_ir_flux * earth_view
        )

        while remaining_s > 0.0:
            step_s = min(thermal_config.max_step_s, remaining_s)
            emitted_w = (
                ir_emissivity
                * STEFAN_BOLTZMANN_W_M2_K4
                * area
                * (np.maximum(face_temp_k, min_temp_k) ** 4 - deep_space_temp_k4)
            )
            conductive_to_faces_w = conductance * (internal_temp_k - face_temp_k)

            face_temp_k += step_s * (
                absorbed_w + conductive_to_faces_w - emitted_w
            ) / face_heat_capacity
            internal_temp_k += step_s * (
                interval_power_w - float(np.sum(conductive_to_faces_w))
            ) / thermal_config.internal_heat_capacity_j_k

            face_temp_k = np.maximum(face_temp_k, min_temp_k)
            internal_temp_k = max(internal_temp_k, min_temp_k)
            remaining_s -= step_s

        sample_solar_view, sample_earth_view = _dynamic_view_factors(env.iloc[index])
        record(target_t_s, float(power_profile[index]), sample_solar_view, sample_earth_view)

    timeseries = pd.DataFrame(rows)
    component_limit_flags = {
        "internal_cold": bool(timeseries["internal_cold_limit_flag"].any()),
        "internal_hot": bool(timeseries["internal_hot_limit_flag"].any()),
        "external_cold": bool(timeseries["external_cold_limit_flag"].any()),
        "external_hot": bool(timeseries["external_hot_limit_flag"].any()),
    }
    face_temperature_columns = [f"temp_{face}_k" for face in FACE_NAMES]
    min_internal_temp_k = float(timeseries["temp_internal_k"].min())
    max_internal_temp_k = float(timeseries["temp_internal_k"].max())
    min_external_temp_k = float(timeseries[face_temperature_columns].min().min())
    max_external_temp_k = float(timeseries[face_temperature_columns].max().max())
    internal_cold_margin_k = min_internal_temp_k - thermal_config.internal_min_operating_k
    internal_hot_margin_k = thermal_config.internal_max_operating_k - max_internal_temp_k
    external_cold_margin_k = min_external_temp_k - thermal_config.external_min_operating_k
    external_hot_margin_k = thermal_config.external_max_operating_k - max_external_temp_k
    worst_cold_margin_k = min(internal_cold_margin_k, external_cold_margin_k)
    worst_hot_margin_k = min(internal_hot_margin_k, external_hot_margin_k)
    summary: dict[str, object] = {
        "coating": canonical_coating,
        "face_coatings": dict(zip(FACE_NAMES, coating_names, strict=True)),
        "attitude_assumption": "LVLH/nadir-pointing bus; not ADCS quaternion coupled",
        "power_w": float(np.mean(power_profile)),
        "average_power_w": float(np.mean(power_profile)),
        "peak_power_w": float(np.max(power_profile)),
        "duration_s": float(timeseries["t_s"].iloc[-1] - timeseries["t_s"].iloc[0]),
        "min_temp_k": float(timeseries["temp_min_k"].min()),
        "max_temp_k": float(timeseries["temp_max_k"].max()),
        "final_internal_temp_k": float(timeseries["temp_internal_k"].iloc[-1]),
        "min_internal_temp_k": min_internal_temp_k,
        "max_internal_temp_k": max_internal_temp_k,
        "min_external_temp_k": min_external_temp_k,
        "max_external_temp_k": max_external_temp_k,
        "internal_cold_margin_k": float(internal_cold_margin_k),
        "internal_hot_margin_k": float(internal_hot_margin_k),
        "external_cold_margin_k": float(external_cold_margin_k),
        "external_hot_margin_k": float(external_hot_margin_k),
        "worst_cold_margin_k": float(worst_cold_margin_k),
        "worst_hot_margin_k": float(worst_hot_margin_k),
        "worst_operating_margin_k": float(min(worst_cold_margin_k, worst_hot_margin_k)),
        "component_limit_flags": component_limit_flags,
        "component_limit_flag": any(component_limit_flags.values()),
    }
    return timeseries, summary
