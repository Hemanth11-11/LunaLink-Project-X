"""IGRF vs aligned-dipole magnetic-field comparison for ADCS.

The brief allows either an IGRF or a dipole B-field. LunaLink propagates with the
transparent aligned dipole; this module cross-checks that choice against the full
IGRF-14 model (via the optional ``ppigrf`` package) and quantifies the error.

The comparison is on field *magnitude* |B|, which sets the available magnetorquer
torque authority (|tau| <= m|B|). ``ppigrf.igrf`` takes geodetic longitude,
latitude and height (km), matching the environment table's ``lat_rad``,
``lon_rad`` and geodetic ``alt_m``. If ``ppigrf`` is not installed the comparison
degrades gracefully so the tool still runs on a clean install.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd

from .constants import RAD2DEG
from .environment import parse_epoch_utc


def igrf_field_magnitude_t(
    lat_deg: float, lon_deg: float, alt_km: float, date: datetime
) -> float | None:
    """Return the IGRF-14 field magnitude (tesla) or ``None`` if ppigrf is absent."""

    try:
        import ppigrf
    except ImportError:
        return None
    east_nt, north_nt, up_nt = ppigrf.igrf(lon_deg, lat_deg, alt_km, date)
    components = np.array([np.ravel(east_nt)[0], np.ravel(north_nt)[0], np.ravel(up_nt)[0]])
    return float(np.linalg.norm(components)) * 1.0e-9


def dipole_vs_igrf(
    environment: pd.DataFrame, epoch_utc: str, sample_stride: int = 20
) -> dict[str, float | bool | int]:
    """Compare aligned-dipole and IGRF field magnitude along the orbit.

    Returns availability plus the mean IGRF/dipole magnitude ratio and the maximum
    relative difference over the sampled points.
    """

    epoch = parse_epoch_utc(epoch_utc).replace(tzinfo=None)
    sampled = environment.iloc[:: max(1, int(sample_stride))]
    ratios: list[float] = []
    for row in sampled.itertuples(index=False):
        igrf_t = igrf_field_magnitude_t(
            row.lat_rad * RAD2DEG, row.lon_rad * RAD2DEG, row.alt_m / 1000.0, epoch
        )
        if igrf_t is None:
            return {"igrf_available": False, "n_samples": 0}
        dipole_t = float(np.linalg.norm([row.b_eci_x_t, row.b_eci_y_t, row.b_eci_z_t]))
        if dipole_t > 0.0:
            ratios.append(igrf_t / dipole_t)
    if not ratios:
        return {"igrf_available": True, "n_samples": 0}
    ratio_array = np.array(ratios)
    return {
        "igrf_available": True,
        "n_samples": int(len(ratios)),
        "mean_igrf_dipole_ratio": float(np.mean(ratio_array)),
        "max_relative_difference": float(np.max(np.abs(ratio_array - 1.0))),
    }
