"""Radiation-belt dose and 5-year solar-array degradation for LunaLink.

A Molniya orbit sweeps from a 500 km perigee out through the proton and electron
Van Allen belts to a 36,000 km apogee on every revolution, so radiation drives
the end-of-life (EOL) solar-array sizing. This module is a transparent,
parametric engineering estimate — it is not AE9/AP9, but its structure (McIlwain
L-shell, belt electron flux, 1-MeV-equivalent fluence, coverglass shielding,
triple-junction degradation) follows the standard method and its numbers are
anchored to published values.

References:
- NASA Small Spacecraft SoA, Power chapter (array degradation for MEO/HEO).
- Vette (1991), AE-8 trapped electron model (order-of-magnitude belt fluxes).
- Space Mission Analysis and Design (SMAD), radiation environment chapter.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .constants import EARTH_RADIUS_M

# AE-8-class omnidirectional >1 MeV trapped-electron flux vs McIlwain L
# (electrons cm^-2 s^-1, order of magnitude). Outer belt peaks near L ~ 4-5.
_L_KNOTS = np.array([1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0])
_FLUX_KNOTS = np.array(
    [3e4, 1e5, 4e5, 3e5, 8e5, 4e6, 1.2e7, 1.5e7, 8e6, 1.5e6, 3e5, 6e4]
)
# Coverglass shielding transmission of >1 MeV-equivalent fluence (150 um CMG).
COVERGLASS_TRANSMISSION = 0.35
# Ionizing dose behind ~2.5 mm (100 mil) Al per incident >1 MeV electron cm^-2
# (SHIELDOSE-2 class order of magnitude), in krad(Si).
DOSE_KRAD_PER_ELECTRON_CM2 = 5.0e-13
# Triple-junction GaAs remaining max-power factor vs 1 MeV electron fluence
# (P/P0), from published JPL/AZUR datasheet-class curves.
_FLUENCE_KNOTS = np.array([0.0, 1e13, 5e13, 1e14, 5e14, 1e15, 5e15])
_PMP_FACTOR_KNOTS = np.array([1.0, 0.98, 0.95, 0.93, 0.87, 0.83, 0.72])


def mcilwain_l(environment: pd.DataFrame) -> np.ndarray:
    """Dipole McIlwain L-shell for each sample: L = (r/Re) / cos^2(lambda_m)."""

    x = environment["x_eci_m"].to_numpy()
    y = environment["y_eci_m"].to_numpy()
    z = environment["z_eci_m"].to_numpy()
    radius = np.sqrt(x**2 + y**2 + z**2)
    magnetic_lat = np.arcsin(np.clip(z / radius, -1.0, 1.0))
    return (radius / EARTH_RADIUS_M) / np.cos(magnetic_lat) ** 2


def trapped_electron_flux(l_shell: np.ndarray) -> np.ndarray:
    """Interpolated >1 MeV trapped-electron flux (cm^-2 s^-1) vs L-shell."""

    log_flux = np.interp(l_shell, _L_KNOTS, np.log10(_FLUX_KNOTS),
                         left=math.log10(_FLUX_KNOTS[0]), right=-1.0)
    return np.where((l_shell >= 1.05) & (l_shell <= 9.0), 10.0**log_flux, 0.0)


def array_remaining_power_factor(fluence_1mev: float) -> float:
    """Remaining max-power factor P/P0 for a given 1 MeV electron fluence."""

    return float(np.interp(fluence_1mev, _FLUENCE_KNOTS, _PMP_FACTOR_KNOTS))


@dataclass(frozen=True)
class RadiationSummary:
    peak_l_shell: float
    fraction_in_belts: float
    annual_fluence_1mev_e_cm2: float
    fluence_5yr_1mev_e_cm2: float
    array_remaining_power_5yr: float
    annual_dose_krad_si_estimate: float
    note: str


def radiation_summary(environment: pd.DataFrame, years: float = 5.0) -> RadiationSummary:
    """Belt exposure, 5-year fluence and derived solar-array degradation."""

    times = environment["t_s"].to_numpy()
    if len(times) < 2:
        raise ValueError("environment must have at least two samples")
    dt = np.diff(times, append=times[-1] + (times[-1] - times[-2]))
    l_shell = mcilwain_l(environment)
    flux = trapped_electron_flux(l_shell)

    span_s = float(times[-1] - times[0]) or 1.0
    # Orbit-average incident fluence rate behind coverglass, scaled to a year.
    incident_per_window = float(np.sum(flux * dt)) * COVERGLASS_TRANSMISSION
    seconds_per_year = 365.25 * 86400.0
    annual_fluence = incident_per_window / span_s * seconds_per_year
    fluence_total = annual_fluence * years

    # Incident (pre-coverglass) fluence drives the structural-shield dose.
    incident_annual_fluence = annual_fluence / COVERGLASS_TRANSMISSION
    annual_dose_krad = incident_annual_fluence * DOSE_KRAD_PER_ELECTRON_CM2

    return RadiationSummary(
        peak_l_shell=float(np.max(l_shell)),
        fraction_in_belts=float(np.mean((l_shell >= 2.0) & (l_shell <= 7.0))),
        annual_fluence_1mev_e_cm2=annual_fluence,
        fluence_5yr_1mev_e_cm2=fluence_total,
        array_remaining_power_5yr=array_remaining_power_factor(fluence_total),
        annual_dose_krad_si_estimate=annual_dose_krad,
        note="Parametric AE-8-class belt model; engineering estimate, not AE9/AP9.",
    )
