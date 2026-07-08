"""Validation metrics for LunaLink simulation outputs."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal

import pandas as pd

from .config import MissionConfig
from .orbit_analysis import CRITICAL_INCLINATION_RAD, secular_rates_rad_s

MetricStatus = Literal["pass", "warn", "fail"]


@dataclass(frozen=True)
class ValidationMetric:
    name: str
    value: float | str
    criterion: str
    status: MetricStatus
    severity: str
    source_module: str

    def to_dict(self) -> dict[str, float | str]:
        return asdict(self)


def _metric(
    name: str,
    value: float | str,
    criterion: str,
    status: MetricStatus,
    source_module: str,
    severity: str = "major",
) -> ValidationMetric:
    return ValidationMetric(
        name=name,
        value=value,
        criterion=criterion,
        status=status,
        severity=severity,
        source_module=source_module,
    )


def validate_environment_table(
    config: MissionConfig, environment: pd.DataFrame
) -> list[ValidationMetric]:
    """Validate the shared orbit/environment table."""

    metrics: list[ValidationMetric] = []
    period_h = config.orbit.period_s / 3600.0
    duration_h = float(environment["t_s"].iloc[-1]) / 3600.0
    min_alt_km = float(environment["altitude_m"].min()) / 1000.0
    max_alt_km = float(environment["altitude_m"].max()) / 1000.0

    metrics.append(
        _metric(
            "fixed_altitude_orbit_period_h",
            period_h,
            "Expected about 10.6845 h for 500 x 36,000 km orbit",
            "pass" if abs(period_h - 10.6845) < 0.01 else "fail",
            "orbit",
            "critical",
        )
    )
    metrics.append(
        _metric(
            "simulation_duration_h",
            duration_h,
            "Must be at least 36 h",
            "pass" if duration_h >= 36.0 else "fail",
            "environment",
            "critical",
        )
    )
    metrics.append(
        _metric(
            "minimum_altitude_km",
            min_alt_km,
            "Should remain near the 500 km perigee altitude",
            "pass" if 450.0 <= min_alt_km <= 550.0 else "warn",
            "orbit",
        )
    )
    metrics.append(
        _metric(
            "maximum_altitude_km",
            max_alt_km,
            "Should remain near the 36,000 km apogee altitude with J2 tolerance",
            "pass" if 35_500.0 <= max_alt_km <= 36_500.0 else "warn",
            "orbit",
        )
    )

    inclination_deg = math.degrees(config.orbit.inclination_rad)
    critical_deg = math.degrees(CRITICAL_INCLINATION_RAD)
    metrics.append(
        _metric(
            "orbit_critical_inclination_deg",
            inclination_deg,
            f"Inclination should sit at the {critical_deg:.2f} deg critical value",
            "pass" if abs(inclination_deg - critical_deg) < 0.2 else "warn",
            "orbit_analysis",
        )
    )
    _, argp_rate = secular_rates_rad_s(
        config.orbit.semi_major_axis_m, config.orbit.eccentricity, config.orbit.inclination_rad
    )
    argp_rate_deg_day = math.degrees(argp_rate) * 86400.0
    metrics.append(
        _metric(
            "orbit_frozen_apsides_argp_rate_deg_per_day",
            argp_rate_deg_day,
            "Apsidal drift must be near zero (Orekit-verified 0.004 deg/day at 63.4 deg)",
            "pass" if abs(argp_rate_deg_day) < 0.02 else "warn",
            "orbit_analysis",
        )
    )

    contact_rows = environment[environment["gs_contact_flag"]]
    if contact_rows.empty:
        metrics.append(
            _metric(
                "ground_station_contacts",
                "none",
                "At least one contact should appear in the 36 h baseline",
                "warn",
                "environment",
            )
        )
    else:
        min_contact_el = float(contact_rows["gs_elevation_rad"].min())
        metrics.append(
            _metric(
                "minimum_contact_elevation_rad",
                min_contact_el,
                "All contacts must be above configured minimum elevation",
                "pass" if min_contact_el >= config.ground_station.min_elevation_rad else "fail",
                "environment",
                "critical",
            )
        )

    eclipse_count = int(environment["eclipse_flag"].sum())
    metrics.append(
        _metric(
            "eclipse_samples",
            eclipse_count,
            "Eclipse count is scenario-dependent; value is recorded for evidence",
            "pass",
            "environment",
            "minor",
        )
    )

    return metrics


def validate_subsystem_summaries(
    summaries: dict[str, dict],
    config: MissionConfig | None = None,
) -> list[ValidationMetric]:
    """Validate major subsystem margins recorded in mission summaries."""

    eps = summaries.get("eps", {})
    thermal = summaries.get("thermal", {})
    adcs = summaries.get("adcs", {})
    pointing = summaries.get("adcs_pointing", {})
    ttc = summaries.get("ttc", {})
    radiation = summaries.get("radiation", {})
    magnetic = summaries.get("magnetic", {})
    comms = summaries.get("comms", {})
    eol_power_budget_w = None if config is None else float(config.spacecraft.eol_power_budget_w)
    xband_margin_db = _optional_float(ttc.get("xband_min_margin_db"))
    uhf_margin_db = _optional_float(ttc.get("uhf_min_margin_db"))
    thermal_margin_k = _optional_float(thermal.get("worst_operating_margin_k"))

    metrics = [
        _metric(
            "eps_minimum_state_of_charge",
            float(eps.get("min_soc", -1.0)),
            "Preliminary EPS reserve should stay at or above 20% SOC",
            "pass" if float(eps.get("min_soc", -1.0)) >= 0.20 else "warn",
            "eps",
        ),
        _metric(
            "eps_unserved_energy_j",
            float(eps.get("unserved_energy_j", 1.0)),
            "No unserved load energy in the baseline run",
            "pass" if float(eps.get("unserved_energy_j", 1.0)) <= 0.0 else "fail",
            "eps",
            "critical",
        ),
        _metric(
            "eps_array_eol_power_w",
            float(eps.get("array_eol_power_w", 0.0)),
            "Solar array EOL power should meet or exceed the 1.2 kW brief value",
            (
                "pass"
                if eol_power_budget_w is None
                or float(eps.get("array_eol_power_w", 0.0)) >= eol_power_budget_w
                else "fail"
            ),
            "eps",
            "critical",
        ),
        _metric(
            "eps_peak_load_w",
            float(eps.get("peak_load_w", 1.0e9)),
            "Peak modeled load should not exceed the 1.2 kW EOL power budget",
            (
                "pass"
                if eol_power_budget_w is None
                or float(eps.get("peak_load_w", 1.0e9)) <= eol_power_budget_w
                else "fail"
            ),
            "eps",
            "critical",
        ),
        _metric(
            "eps_average_load_w",
            float(eps.get("average_load_w", 1.0e9)),
            "Average modeled load should stay below the 1.2 kW EOL power budget",
            (
                "pass"
                if eol_power_budget_w is None
                or float(eps.get("average_load_w", 1.0e9)) <= eol_power_budget_w
                else "fail"
            ),
            "eps",
            "critical",
        ),
        _metric(
            "thermal_component_limit_flag",
            str(bool(thermal.get("component_limit_flag", True))),
            "No thermal component limit flags in the baseline run",
            "pass" if not bool(thermal.get("component_limit_flag", True)) else "fail",
            "thermal",
            "critical",
        ),
        _metric(
            "thermal_worst_operating_margin_k",
            "none" if thermal_margin_k is None else thermal_margin_k,
            "Preliminary hot/cold thermal margin should be at least 5 K",
            "pass" if thermal_margin_k is not None and thermal_margin_k >= 5.0 else "warn",
            "thermal",
        ),
        _metric(
            "adcs_final_angular_speed_deg_s",
            float(adcs.get("final_angular_speed_deg_s", 1.0e9)),
            "Detumble demonstration should end below 0.05 deg/s",
            "pass" if float(adcs.get("final_angular_speed_deg_s", 1.0e9)) <= 0.05 else "warn",
            "adcs",
        ),
        _metric(
            "adcs_wheel_saturated",
            str(bool(adcs.get("wheel_saturated", True))),
            "Preliminary disturbance momentum bookkeeping should not exceed assumed capacity",
            "pass" if not bool(adcs.get("wheel_saturated", True)) else "fail",
            "adcs",
            "critical",
        ),
        _metric(
            "ttc_xband_min_margin_db",
            "none" if xband_margin_db is None else xband_margin_db,
            "X-band link margin should exceed the 3 dB threshold",
            "pass" if xband_margin_db is not None and xband_margin_db >= 3.0 else "fail",
            "ttc",
            "critical",
        ),
        _metric(
            "ttc_uhf_min_margin_db",
            "none" if uhf_margin_db is None else uhf_margin_db,
            "UHF link margin should exceed the 3 dB threshold",
            "pass" if uhf_margin_db is not None and uhf_margin_db >= 3.0 else "fail",
            "ttc",
            "critical",
        ),
        _metric(
            "ttc_xband_data_rate_bps",
            float(ttc.get("xband_data_rate_bps", 0.0)),
            "Earth downlink should meet at least 100 Mbps when available",
            "pass" if float(ttc.get("xband_data_rate_bps", 0.0)) >= 100.0e6 else "fail",
            "ttc",
            "critical",
        ),
    ]
    if pointing:
        settled_max = float(pointing.get("settled_max_pointing_error_deg", 99.0))
        metrics.append(
            _metric(
                "adcs_sun_pointing_settled_error_deg",
                settled_max,
                "Closed-loop sun-pointing should settle below its 3 deg requirement",
                "pass" if bool(pointing.get("pointing_requirement_met", False)) else "warn",
                "adcs",
            )
        )
    if magnetic and magnetic.get("igrf_available"):
        max_rel_diff = float(magnetic.get("max_relative_difference", 1.0))
        metrics.append(
            _metric(
                "adcs_dipole_vs_igrf_max_rel_diff",
                max_rel_diff,
                "Aligned dipole should track IGRF-14 magnitude within ~40%",
                "pass" if max_rel_diff < 0.4 else "warn",
                "adcs",
                "minor",
            )
        )
    if comms:
        atmos_5deg = float(comms.get("atmos_loss_5deg_db", 0.0))
        metrics.append(
            _metric(
                "ttc_xband_atmos_loss_5deg_db",
                atmos_5deg,
                "ITU-R X-band rain+gas loss at 5 deg should be a credible 1-6 dB",
                "pass" if 1.0 <= atmos_5deg <= 6.0 else "warn",
                "comms",
            )
        )
        metrics.append(
            _metric(
                "ttc_ccsds_coding_gain_db",
                float(comms.get("ccsds_coding_gain_db", 0.0)),
                "CCSDS coding should provide several dB of gain over uncoded BPSK",
                "pass" if float(comms.get("ccsds_coding_gain_db", 0.0)) >= 3.0 else "warn",
                "comms",
                "minor",
            )
        )
    if radiation:
        annual_dose = float(radiation.get("annual_dose_krad_si_estimate", 0.0))
        array_remaining = float(radiation.get("array_remaining_power_5yr", 0.0))
        metrics.append(
            _metric(
                "radiation_annual_dose_krad",
                annual_dose,
                "Belt dose should be a credible 5-60 krad(Si)/yr for this HEO",
                "pass" if 5.0 <= annual_dose <= 60.0 else "warn",
                "radiation",
            )
        )
        metrics.append(
            _metric(
                "radiation_array_remaining_power_5yr",
                array_remaining,
                "Derived 5-yr array power fraction should stay above 0.80",
                "pass" if array_remaining >= 0.80 else "warn",
                "radiation",
            )
        )
    return metrics


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def metrics_to_dataframe(metrics: list[ValidationMetric]) -> pd.DataFrame:
    return pd.DataFrame([metric.to_dict() for metric in metrics])


def has_critical_failures(metrics: list[ValidationMetric]) -> bool:
    return any(metric.status == "fail" and metric.severity == "critical" for metric in metrics)
