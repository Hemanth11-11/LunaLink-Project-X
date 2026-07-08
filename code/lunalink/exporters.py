"""Scenario export helpers for external astrodynamics tools."""

from __future__ import annotations

from pathlib import Path

from .config import MissionConfig
from .constants import RAD2DEG
from .io import ensure_directory, write_json


def write_scenario_exports(config: MissionConfig, output_dir: str | Path) -> dict[str, str]:
    """Write simple GMAT/Orekit-style starting scenarios from the active config."""

    directory = ensure_directory(output_dir)
    gmat_path = directory / "LunaLink_GMAT_scenario.script"
    orekit_path = directory / "LunaLink_Orekit_scenario.json"
    recipe_path = directory / "LunaLink_external_validation_recipe.md"
    comparison_template_path = directory / "LunaLink_external_comparison_template.csv"

    orbit = config.orbit
    spacecraft = config.spacecraft
    ground = config.ground_station
    sma_km = orbit.semi_major_axis_m / 1000.0

    gmat_path.write_text(
        "\n".join(
            [
                "% LunaLink GMAT-style scenario export",
                "% This is an interchange starting point, not a validated GMAT truth run.",
                "Create Spacecraft LunaLink;",
                "LunaLink.DateFormat = UTCGregorian;",
                f"LunaLink.Epoch = '{config.simulation.epoch_utc}';",
                "LunaLink.CoordinateSystem = EarthMJ2000Eq;",
                "LunaLink.DisplayStateType = Keplerian;",
                f"LunaLink.SMA = {sma_km:.6f};",
                f"LunaLink.ECC = {orbit.eccentricity:.12f};",
                f"LunaLink.INC = {orbit.inclination_rad * RAD2DEG:.6f};",
                f"LunaLink.RAAN = {orbit.raan_rad * RAD2DEG:.6f};",
                f"LunaLink.AOP = {orbit.argument_of_perigee_rad * RAD2DEG:.6f};",
                f"LunaLink.TA = {orbit.true_anomaly_at_epoch_rad * RAD2DEG:.6f};",
                f"LunaLink.DryMass = {spacecraft.mass_kg:.3f};",
                "",
                "Create GroundStation Ottobrunn;",
                f"Ottobrunn.Location1 = {ground.latitude_rad * RAD2DEG:.8f};",
                f"Ottobrunn.Location2 = {ground.longitude_rad * RAD2DEG:.8f};",
                f"Ottobrunn.Location3 = {ground.altitude_m / 1000.0:.6f};",
                f"% Minimum elevation deg: {ground.min_elevation_rad * RAD2DEG:.3f}",
                "",
                "% Recommended validation products to add in GMAT:",
                "% - Propagate for 36 h with Earth point-mass + J2.",
                "% - Use EarthMJ2000Eq/EME2000-like inertial output.",
                "% - Report elapsed time, position, velocity, altitude, and station elevation.",
                "% - Add eclipse/umbra and line-of-sight access events if available.",
                "% - Compare event times against the companion CSV tolerances.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    write_json(
        orekit_path,
        {
            "name": "LunaLink",
            "note": "Orekit-style JSON scenario seed; validate independently before use.",
            "epoch_utc": config.simulation.epoch_utc,
            "orbit_frame": "EME2000",
            "central_body": "Earth",
            "keplerian": {
                "semi_major_axis_m": orbit.semi_major_axis_m,
                "eccentricity": orbit.eccentricity,
                "inclination_deg": orbit.inclination_rad * RAD2DEG,
                "raan_deg": orbit.raan_rad * RAD2DEG,
                "argument_of_perigee_deg": orbit.argument_of_perigee_rad * RAD2DEG,
                "true_anomaly_deg": orbit.true_anomaly_at_epoch_rad * RAD2DEG,
            },
            "spacecraft": {
                "mass_kg": spacecraft.mass_kg,
                "dimensions_m": [
                    spacecraft.length_x_m,
                    spacecraft.length_y_m,
                    spacecraft.length_z_m,
                ],
            },
            "ground_station": {
                "name": ground.name,
                "latitude_deg": ground.latitude_rad * RAD2DEG,
                "longitude_deg": ground.longitude_rad * RAD2DEG,
                "altitude_m": ground.altitude_m,
                "min_elevation_deg": ground.min_elevation_rad * RAD2DEG,
            },
            "validation_recipe": {
                "duration_s": config.simulation.duration_s,
                "output_step_s": config.simulation.output_step_s,
                "force_model": "Earth point mass plus J2 for first-order correlation",
                "earth_shape": "WGS84 station geometry; match tool defaults explicitly",
                "events": ["ground elevation crossing", "eclipse entry/exit"],
                "comparison_template": str(comparison_template_path.name),
            },
        },
    )
    recipe_path.write_text(
        "\n".join(
            [
                "# LunaLink External Validation Recipe",
                "",
                "This package is a reproducible starting point for GMAT or Orekit",
                "correlation. It is not itself an executed external validation result.",
                "",
                "## Required External Products",
                "",
                "1. Orbit period, perigee altitude, and apogee altitude over 36 h.",
                "2. Ground-station access start/end times at the 5 deg elevation mask.",
                "3. Eclipse entry/exit times using a documented shadow model.",
                "4. A signed or dated comparison table using the companion CSV schema.",
                "",
                "## Recommended Tolerances",
                "",
                "- Orbit period: 60 s for point-mass/J2 first-order correlation.",
                "- Altitude envelope: 25 km for matched initial conditions and J2.",
                "- Access/eclipses: one output step unless event-refined outputs are enabled.",
                "",
                "Formal validation remains open until these products are generated by",
                "an independent GMAT/Orekit run and reviewed.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    comparison_template_path.write_text(
        "\n".join(
            [
                "item,lunalink_value,external_tool,external_value,tolerance,units,status,reviewer_notes",
                "orbit_period,,,,60,s,pending,",
                "minimum_altitude,,,,25,km,pending,",
                "maximum_altitude,,,,25,km,pending,",
                "first_contact_start,,,,600,s,pending,",
                "first_contact_end,,,,600,s,pending,",
                "first_eclipse_entry,,,,600,s,pending,",
                "first_eclipse_exit,,,,600,s,pending,",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "gmat": str(gmat_path),
        "orekit": str(orekit_path),
        "external_validation_recipe": str(recipe_path),
        "external_comparison_template": str(comparison_template_path),
    }
