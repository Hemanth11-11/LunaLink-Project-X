"""Elevation-dependent atmospheric loss, CCSDS coding, and Doppler for TT&C.

The baseline link budget in ``ttc.py`` uses a single fixed propagation-loss term.
This module refines the Earth X-band downlink with:

- ITU-R P.618/P.676 slant-path attenuation (rain + gas) as a function of
  elevation, via the optional ``itur`` package (gated; falls back to a secant
  gaseous model if absent);
- CCSDS 131.0-B coding schemes (required Eb/N0 at BER 1e-6), giving the coding
  gain over uncoded BPSK; and
- geometric Doppler shift from the ground-station range rate.

The ITU-R computation is expensive, so an elevation -> attenuation lookup is
built once (cached) and interpolated per sample.
"""

from __future__ import annotations

import warnings
from functools import lru_cache

import numpy as np
import pandas as pd

from .constants import SPEED_OF_LIGHT_M_S

# CCSDS 131.0-B required Eb/N0 (dB) at BER 1e-6, near-Earth coded schemes.
CCSDS_REQUIRED_EBN0_DB = {
    "uncoded_bpsk": 10.5,
    "conv_r1_2_k7": 4.8,
    "rs_conv_concatenated": 2.5,
    "turbo_r1_6": 0.6,
    "ldpc_ar4ja_r1_2": 1.1,
}


def ccsds_coding_gain_db(scheme: str) -> float:
    """Coding gain of a CCSDS scheme relative to uncoded BPSK (dB)."""

    if scheme not in CCSDS_REQUIRED_EBN0_DB:
        raise KeyError(f"unknown CCSDS scheme: {scheme}")
    return CCSDS_REQUIRED_EBN0_DB["uncoded_bpsk"] - CCSDS_REQUIRED_EBN0_DB[scheme]


def doppler_shift_hz(frequency_hz: float, range_rate_mps: float) -> float:
    """One-way geometric Doppler shift (Hz). Positive range rate lowers frequency."""

    return -frequency_hz * range_rate_mps / SPEED_OF_LIGHT_M_S


@lru_cache(maxsize=8)
def _itur_elevation_lookup(
    lat_deg: float, lon_deg: float, freq_ghz: float, diameter_m: float, exceedance_pct: float
) -> tuple[tuple[float, ...], tuple[float, ...]] | None:
    try:
        import itur
    except ImportError:
        return None
    elevations = tuple(float(e) for e in range(5, 91, 5))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        attenuations = tuple(
            float(
                itur.atmospheric_attenuation_slant_path(
                    lat_deg, lon_deg, freq_ghz, el, exceedance_pct, diameter_m
                ).value
            )
            for el in elevations
        )
    return elevations, attenuations


def slant_attenuation_db(
    elevation_deg: float, lat_deg: float, lon_deg: float, freq_ghz: float,
    diameter_m: float, exceedance_pct: float = 1.0,
) -> float:
    """Atmospheric attenuation (dB) at a given elevation, ITU-R or fallback."""

    lookup = _itur_elevation_lookup(lat_deg, lon_deg, freq_ghz, diameter_m, exceedance_pct)
    clamped_el = max(5.0, min(90.0, float(elevation_deg)))
    if lookup is None:
        # Fallback: ~0.2 dB zenith gaseous absorption scaled by the slant secant.
        return 0.2 / max(np.sin(np.radians(clamped_el)), 0.09)
    elevations, attenuations = lookup
    return float(np.interp(clamped_el, elevations, attenuations))


def comms_atmosphere_summary(
    environment: pd.DataFrame,
    ground_lat_deg: float,
    ground_lon_deg: float,
    freq_ghz: float = 8.4,
    rx_diameter_m: float = 3.0,
    exceedance_pct: float = 1.0,
    ccsds_scheme: str = "rs_conv_concatenated",
) -> dict[str, float | bool | str]:
    """Elevation-dependent X-band atmospheric loss, coding gain and Doppler."""

    lookup = _itur_elevation_lookup(
        ground_lat_deg, ground_lon_deg, freq_ghz, rx_diameter_m, exceedance_pct
    )
    contact = environment["gs_contact_flag"].to_numpy(dtype=bool)
    elevation_deg = environment["gs_elevation_rad"].to_numpy() * (180.0 / np.pi)
    atten = np.array(
        [
            slant_attenuation_db(
                el, ground_lat_deg, ground_lon_deg, freq_ghz, rx_diameter_m, exceedance_pct
            )
            for el in elevation_deg
        ]
    )

    times = environment["t_s"].to_numpy()
    ranges = environment["gs_range_m"].to_numpy()
    range_rate = np.gradient(ranges, times)
    doppler_hz = np.abs(doppler_shift_hz(freq_ghz * 1e9, range_rate))

    contact_atten = atten[contact] if contact.any() else atten
    contact_doppler = doppler_hz[contact] if contact.any() else doppler_hz
    return {
        "itur_available": lookup is not None,
        "atmos_loss_5deg_db": slant_attenuation_db(
            5.0, ground_lat_deg, ground_lon_deg, freq_ghz, rx_diameter_m, exceedance_pct
        ),
        "atmos_loss_zenith_db": slant_attenuation_db(
            90.0, ground_lat_deg, ground_lon_deg, freq_ghz, rx_diameter_m, exceedance_pct
        ),
        "atmos_loss_contact_mean_db": float(np.mean(contact_atten)),
        "atmos_loss_contact_max_db": float(np.max(contact_atten)),
        "ccsds_scheme": ccsds_scheme,
        "ccsds_required_ebn0_db": float(CCSDS_REQUIRED_EBN0_DB[ccsds_scheme]),
        "ccsds_coding_gain_db": ccsds_coding_gain_db(ccsds_scheme),
        "max_doppler_khz": float(np.max(contact_doppler)) / 1e3,
        "exceedance_pct": float(exceedance_pct),
    }
