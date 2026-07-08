"""Reference-frame utilities for the LunaLink simulator."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from .constants import EARTH_FLATTENING, EARTH_RADIUS_M, EARTH_ROT_RATE_RAD_S


def rot_x(angle_rad: float) -> NDArray[np.float64]:
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]], dtype=float)


def rot_z(angle_rad: float) -> NDArray[np.float64]:
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=float)


def eci_to_ecef_matrix(elapsed_s: float, theta0_rad: float = 0.0) -> NDArray[np.float64]:
    """Return the simplified Earth-rotation matrix from ECI to ECEF.

    This phase uses a constant Earth rotation rate. It is sufficient for contact-window
    simulation over the 36 h assignment window and keeps the frame model transparent.
    """

    return rot_z(theta0_rad - EARTH_ROT_RATE_RAD_S * elapsed_s)


def geodetic_to_ecef(
    latitude_rad: float, longitude_rad: float, altitude_m: float = 0.0
) -> NDArray[np.float64]:
    """Convert WGS84 geodetic coordinates to ECEF."""

    sin_lat = np.sin(latitude_rad)
    cos_lat = np.cos(latitude_rad)
    eccentricity_sq = EARTH_FLATTENING * (2.0 - EARTH_FLATTENING)
    prime_vertical_radius = EARTH_RADIUS_M / np.sqrt(1.0 - eccentricity_sq * sin_lat**2)

    x = (prime_vertical_radius + altitude_m) * cos_lat * np.cos(longitude_rad)
    y = (prime_vertical_radius + altitude_m) * cos_lat * np.sin(longitude_rad)
    z = (prime_vertical_radius * (1.0 - eccentricity_sq) + altitude_m) * sin_lat
    return np.array([x, y, z], dtype=float)


def ecef_to_spherical_lat_lon_alt(r_ecef_m: NDArray[np.float64]) -> tuple[float, float, float]:
    """Return geocentric latitude, longitude, and spherical altitude."""

    radius_m = float(np.linalg.norm(r_ecef_m))
    latitude_rad = float(np.arcsin(r_ecef_m[2] / radius_m))
    longitude_rad = float(np.arctan2(r_ecef_m[1], r_ecef_m[0]))
    altitude_m = radius_m - EARTH_RADIUS_M
    return latitude_rad, longitude_rad, altitude_m


def ecef_to_geodetic_lat_lon_alt(r_ecef_m: NDArray[np.float64]) -> tuple[float, float, float]:
    """Convert ECEF position to WGS84 geodetic latitude, longitude, and altitude."""

    x_m, y_m, z_m = r_ecef_m
    longitude_rad = float(np.arctan2(y_m, x_m))
    semi_major_m = EARTH_RADIUS_M
    eccentricity_sq = EARTH_FLATTENING * (2.0 - EARTH_FLATTENING)
    semi_minor_m = semi_major_m * (1.0 - EARTH_FLATTENING)
    second_eccentricity_sq = (semi_major_m**2 - semi_minor_m**2) / semi_minor_m**2
    horizontal_m = float(np.hypot(x_m, y_m))
    theta_rad = float(np.arctan2(z_m * semi_major_m, horizontal_m * semi_minor_m))
    sin_theta = np.sin(theta_rad)
    cos_theta = np.cos(theta_rad)
    latitude_rad = float(
        np.arctan2(
            z_m + second_eccentricity_sq * semi_minor_m * sin_theta**3,
            horizontal_m - eccentricity_sq * semi_major_m * cos_theta**3,
        )
    )
    sin_lat = np.sin(latitude_rad)
    prime_vertical_radius = semi_major_m / np.sqrt(1.0 - eccentricity_sq * sin_lat**2)
    altitude_m = float(horizontal_m / np.cos(latitude_rad) - prime_vertical_radius)
    return latitude_rad, longitude_rad, altitude_m


def enu_basis(latitude_rad: float, longitude_rad: float) -> tuple[NDArray[np.float64], ...]:
    """Return east, north, up basis vectors in ECEF."""

    sin_lat = np.sin(latitude_rad)
    cos_lat = np.cos(latitude_rad)
    sin_lon = np.sin(longitude_rad)
    cos_lon = np.cos(longitude_rad)

    east = np.array([-sin_lon, cos_lon, 0.0], dtype=float)
    north = np.array([-sin_lat * cos_lon, -sin_lat * sin_lon, cos_lat], dtype=float)
    up = np.array([cos_lat * cos_lon, cos_lat * sin_lon, sin_lat], dtype=float)
    return east, north, up


def topocentric_az_el_range(
    r_target_ecef_m: NDArray[np.float64],
    r_station_ecef_m: NDArray[np.float64],
    station_latitude_rad: float,
    station_longitude_rad: float,
) -> tuple[float, float, float]:
    """Return azimuth, elevation, and range from a ground station to a target."""

    rho_m = r_target_ecef_m - r_station_ecef_m
    range_m = float(np.linalg.norm(rho_m))
    east, north, up = enu_basis(station_latitude_rad, station_longitude_rad)

    east_m = float(np.dot(rho_m, east))
    north_m = float(np.dot(rho_m, north))
    up_m = float(np.dot(rho_m, up))

    elevation_rad = float(np.arctan2(up_m, np.hypot(east_m, north_m)))
    azimuth_rad = float(np.mod(np.arctan2(east_m, north_m), 2.0 * np.pi))
    return azimuth_rad, elevation_rad, range_m
