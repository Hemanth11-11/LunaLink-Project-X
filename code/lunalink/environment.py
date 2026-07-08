"""Orbit-derived environment table for the LunaLink simulator."""

from __future__ import annotations

from datetime import UTC, datetime

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from .config import MissionConfig
from .constants import (
    DEG2RAD,
    EARTH_EQUATORIAL_B_T,
    EARTH_RADIUS_M,
    SOLAR_CONSTANT_W_M2,
)
from .frames import (
    ecef_to_geodetic_lat_lon_alt,
    eci_to_ecef_matrix,
    geodetic_to_ecef,
    topocentric_az_el_range,
)
from .orbit import propagate_orbit


def parse_epoch_utc(epoch_utc: str) -> datetime:
    if epoch_utc.endswith("Z"):
        epoch_utc = epoch_utc[:-1] + "+00:00"
    parsed = datetime.fromisoformat(epoch_utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def julian_date(epoch: datetime, elapsed_s: float = 0.0) -> float:
    unix_seconds = epoch.timestamp() + elapsed_s
    return unix_seconds / 86_400.0 + 2_440_587.5


def _unit(vector: NDArray[np.float64]) -> NDArray[np.float64]:
    return vector / np.linalg.norm(vector)


def approximate_sun_hat_eci(epoch: datetime, elapsed_s: float) -> NDArray[np.float64]:
    """Low-precision Earth-to-Sun unit vector in an ECI-like equatorial frame."""

    days_since_j2000 = julian_date(epoch, elapsed_s) - 2_451_545.0
    mean_longitude_rad = (280.460 + 0.9856474 * days_since_j2000) * DEG2RAD
    mean_anomaly_rad = (357.528 + 0.9856003 * days_since_j2000) * DEG2RAD
    ecliptic_longitude_rad = mean_longitude_rad + (
        1.915 * np.sin(mean_anomaly_rad) + 0.020 * np.sin(2.0 * mean_anomaly_rad)
    ) * DEG2RAD
    obliquity_rad = (23.439 - 0.0000004 * days_since_j2000) * DEG2RAD

    return _unit(
        np.array(
            [
                np.cos(ecliptic_longitude_rad),
                np.cos(obliquity_rad) * np.sin(ecliptic_longitude_rad),
                np.sin(obliquity_rad) * np.sin(ecliptic_longitude_rad),
            ],
            dtype=float,
        )
    )


def approximate_moon_position_eci_m(epoch: datetime, elapsed_s: float) -> NDArray[np.float64]:
    """Low-precision geocentric Moon position for contact geometry screening."""

    days_since_j2000 = julian_date(epoch, elapsed_s) - 2_451_545.0
    mean_longitude_rad = (218.316 + 13.176396 * days_since_j2000) * DEG2RAD
    mean_anomaly_rad = (134.963 + 13.064993 * days_since_j2000) * DEG2RAD
    argument_latitude_rad = (93.272 + 13.229350 * days_since_j2000) * DEG2RAD
    ecliptic_longitude_rad = mean_longitude_rad + 6.289 * DEG2RAD * np.sin(mean_anomaly_rad)
    ecliptic_latitude_rad = 5.128 * DEG2RAD * np.sin(argument_latitude_rad)
    obliquity_rad = (23.439 - 0.0000004 * days_since_j2000) * DEG2RAD
    distance_m = 384_400_000.0

    x_ecl = np.cos(ecliptic_latitude_rad) * np.cos(ecliptic_longitude_rad)
    y_ecl = np.cos(ecliptic_latitude_rad) * np.sin(ecliptic_longitude_rad)
    z_ecl = np.sin(ecliptic_latitude_rad)

    return distance_m * np.array(
        [
            x_ecl,
            np.cos(obliquity_rad) * y_ecl - np.sin(obliquity_rad) * z_ecl,
            np.sin(obliquity_rad) * y_ecl + np.cos(obliquity_rad) * z_ecl,
        ],
        dtype=float,
    )


def in_cylindrical_eclipse(r_eci_m: NDArray[np.float64], sun_hat_eci: NDArray[np.float64]) -> bool:
    behind_earth = float(np.dot(r_eci_m, sun_hat_eci)) < 0.0
    perpendicular = r_eci_m - np.dot(r_eci_m, sun_hat_eci) * sun_hat_eci
    return bool(behind_earth and np.linalg.norm(perpendicular) < EARTH_RADIUS_M)


def moon_occulted_by_earth(
    r_sc_eci_m: NDArray[np.float64], r_moon_eci_m: NDArray[np.float64], clearance_m: float = 0.0
) -> bool:
    line_m = r_moon_eci_m - r_sc_eci_m
    s_star = -float(np.dot(r_sc_eci_m, line_m)) / float(np.dot(line_m, line_m))
    s_star = min(1.0, max(0.0, s_star))
    closest_m = r_sc_eci_m + s_star * line_m
    return bool(np.linalg.norm(closest_m) < EARTH_RADIUS_M + clearance_m)


def simple_dipole_field_ecef_t(r_ecef_m: NDArray[np.float64]) -> NDArray[np.float64]:
    """Earth-fixed aligned dipole field for engineering ADCS screening."""

    r_hat = _unit(r_ecef_m)
    dipole_hat = np.array([0.0, 0.0, 1.0], dtype=float)
    scale = EARTH_EQUATORIAL_B_T * (EARTH_RADIUS_M / np.linalg.norm(r_ecef_m)) ** 3
    return scale * (3.0 * np.dot(dipole_hat, r_hat) * r_hat - dipole_hat)


def simple_dipole_field_eci_t(
    r_eci_m: NDArray[np.float64], elapsed_s: float = 0.0
) -> NDArray[np.float64]:
    """Return the simple Earth-fixed dipole field expressed in ECI axes."""

    rotation = eci_to_ecef_matrix(elapsed_s)
    field_ecef_t = simple_dipole_field_ecef_t(rotation @ r_eci_m)
    return rotation.T @ field_ecef_t


def simple_atmosphere_density_kg_m3(altitude_m: float) -> float:
    reference_altitude_m = 500_000.0
    reference_density = 1.0e-12
    scale_height_m = 60_000.0
    if altitude_m > 1_200_000.0:
        return 0.0
    return float(reference_density * np.exp(-(altitude_m - reference_altitude_m) / scale_height_m))


def build_environment_table(config: MissionConfig, include_j2: bool = True) -> pd.DataFrame:
    """Build the shared orbit/environment truth table."""

    orbit_df = propagate_orbit(config, include_j2=include_j2)
    epoch = parse_epoch_utc(config.simulation.epoch_utc)
    station = config.ground_station
    station_ecef_m = geodetic_to_ecef(
        station.latitude_rad, station.longitude_rad, station.altitude_m
    )

    rows: list[dict[str, float | bool]] = []
    for row in orbit_df.itertuples(index=False):
        t_s = float(row.t_s)
        r_eci_m = np.array([row.x_eci_m, row.y_eci_m, row.z_eci_m], dtype=float)
        rotation = eci_to_ecef_matrix(t_s)
        r_ecef_m = rotation @ r_eci_m
        lat_rad, lon_rad, alt_m = ecef_to_geodetic_lat_lon_alt(r_ecef_m)
        az_rad, elevation_rad, range_m = topocentric_az_el_range(
            r_ecef_m, station_ecef_m, station.latitude_rad, station.longitude_rad
        )

        sun_hat = approximate_sun_hat_eci(epoch, t_s)
        moon_position_m = approximate_moon_position_eci_m(epoch, t_s)
        moon_line_m = moon_position_m - r_eci_m
        moon_range_m = float(np.linalg.norm(moon_line_m))
        moon_hat = _unit(moon_line_m)
        eclipse = in_cylindrical_eclipse(r_eci_m, sun_hat)
        radius_m = float(row.radius_m)
        altitude_from_orbit_m = float(row.altitude_m)
        earth_view_scale = (EARTH_RADIUS_M / radius_m) ** 2
        phase_albedo = max(0.0, float(np.dot(_unit(r_eci_m), sun_hat)))
        magnetic_field_eci_t = simple_dipole_field_eci_t(r_eci_m, t_s)

        rows.append(
            {
                "t_s": t_s,
                "x_eci_m": float(row.x_eci_m),
                "y_eci_m": float(row.y_eci_m),
                "z_eci_m": float(row.z_eci_m),
                "vx_eci_mps": float(row.vx_eci_mps),
                "vy_eci_mps": float(row.vy_eci_mps),
                "vz_eci_mps": float(row.vz_eci_mps),
                "x_ecef_m": float(r_ecef_m[0]),
                "y_ecef_m": float(r_ecef_m[1]),
                "z_ecef_m": float(r_ecef_m[2]),
                "lat_rad": lat_rad,
                "lon_rad": lon_rad,
                "alt_m": alt_m,
                "altitude_m": altitude_from_orbit_m,
                "sun_hat_x": float(sun_hat[0]),
                "sun_hat_y": float(sun_hat[1]),
                "sun_hat_z": float(sun_hat[2]),
                "moon_hat_x": float(moon_hat[0]),
                "moon_hat_y": float(moon_hat[1]),
                "moon_hat_z": float(moon_hat[2]),
                "eclipse_flag": eclipse,
                "solar_flux_w_m2": 0.0 if eclipse else SOLAR_CONSTANT_W_M2,
                "gs_range_m": range_m,
                "gs_elevation_rad": elevation_rad,
                "gs_azimuth_rad": az_rad,
                "gs_contact_flag": elevation_rad >= station.min_elevation_rad,
                "moon_range_m": moon_range_m,
                "moon_occulted_flag": moon_occulted_by_earth(r_eci_m, moon_position_m),
                "earth_view_scale": earth_view_scale,
                "earth_ir_flux_w_m2": 237.0 * earth_view_scale,
                "albedo_flux_w_m2": 0.30 * SOLAR_CONSTANT_W_M2 * earth_view_scale * phase_albedo,
                "b_eci_x_t": float(magnetic_field_eci_t[0]),
                "b_eci_y_t": float(magnetic_field_eci_t[1]),
                "b_eci_z_t": float(magnetic_field_eci_t[2]),
                "atmospheric_density_kg_m3": simple_atmosphere_density_kg_m3(
                    altitude_from_orbit_m
                ),
            }
        )

    return pd.DataFrame(rows)
