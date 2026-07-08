"""Mission-level orchestration for LunaLink."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd

from .adcs import run_adcs, run_sun_pointing
from .comms_atmosphere import comms_atmosphere_summary
from .config import MissionConfig, default_mission_config
from .constants import RAD2DEG
from .environment import build_environment_table
from .eps import run_eps
from .magnetic_field import dipole_vs_igrf
from .orbit_analysis import orbit_summary
from .radiation import radiation_summary
from .thermal import ThermalConfig, default_face_coatings, run_thermal
from .ttc import run_ttc
from .validation import ValidationMetric, validate_environment_table, validate_subsystem_summaries


@dataclass(frozen=True)
class MissionResults:
    config: MissionConfig
    environment: pd.DataFrame
    eps: pd.DataFrame
    thermal: pd.DataFrame
    adcs: pd.DataFrame
    ttc: pd.DataFrame
    summaries: dict[str, dict]
    validation_metrics: list[ValidationMetric]


def run_mission(config: MissionConfig | None = None, include_j2: bool = True) -> MissionResults:
    mission_config = config or default_mission_config()
    environment = build_environment_table(mission_config, include_j2=include_j2)
    eps, eps_summary = run_eps(environment)
    ttc, ttc_summary = run_ttc(environment)
    thermal, thermal_summary = run_thermal(
        environment,
        power_w=eps["load_power_w"],
        config=ThermalConfig(face_coatings=default_face_coatings()),
    )
    adcs, adcs_summary = run_adcs(environment, mission_config)
    _, pointing_summary = run_sun_pointing(environment, mission_config)
    summaries = {
        "eps": eps_summary,
        "thermal": thermal_summary,
        "adcs": adcs_summary,
        "adcs_pointing": pointing_summary,
        "ttc": ttc_summary,
        "orbit": orbit_summary(mission_config),
        "radiation": asdict(radiation_summary(environment)),
        "magnetic": dipole_vs_igrf(environment, mission_config.simulation.epoch_utc),
        "comms": comms_atmosphere_summary(
            environment,
            mission_config.ground_station.latitude_rad * RAD2DEG,
            mission_config.ground_station.longitude_rad * RAD2DEG,
        ),
    }
    validation_metrics = [
        *validate_environment_table(mission_config, environment),
        *validate_subsystem_summaries(summaries, mission_config),
    ]
    return MissionResults(
        config=mission_config,
        environment=environment,
        eps=eps,
        thermal=thermal,
        adcs=adcs,
        ttc=ttc,
        summaries=summaries,
        validation_metrics=validation_metrics,
    )
