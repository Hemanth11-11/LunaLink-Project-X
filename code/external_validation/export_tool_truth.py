"""Export LunaLink tool outputs for external SPICE/Orekit cross-check.

Runs in the PROJECT venv (numpy 2.5.1). Writes CSVs the reference script reads.
"""
import numpy as np, pandas as pd
from lunalink.config import default_mission_config, MissionConfig, SimulationConfig
from lunalink.environment import (
    build_environment_table, parse_epoch_utc, approximate_sun_hat_eci,
    approximate_moon_position_eci_m,
)
from lunalink.constants import EARTH_MU_M3_S2, EARTH_RADIUS_M

b = default_mission_config()
cfg = MissionConfig(orbit=b.orbit, spacecraft=b.spacecraft, ground_station=b.ground_station,
                    simulation=SimulationConfig(epoch_utc=b.simulation.epoch_utc,
                                                duration_s=36*3600.0, output_step_s=600.0))
env = build_environment_table(cfg, include_j2=True)
env.to_csv("/tmp/claude-1000/tool_env.csv", index=False)

# Orbit elements + constants for Orekit setup
o = b.orbit
meta = dict(epoch_utc=b.simulation.epoch_utc, a_m=o.semi_major_axis_m, e=o.eccentricity,
            i_rad=o.inclination_rad, raan_rad=o.raan_rad, argp_rad=o.argument_of_perigee_rad,
            nu_rad=o.true_anomaly_at_epoch_rad, mu=EARTH_MU_M3_S2, Re=EARTH_RADIUS_M,
            period_s=o.period_s, perigee_alt_m=o.perigee_altitude_m, apogee_alt_m=o.apogee_altitude_m)
pd.Series(meta).to_csv("/tmp/claude-1000/tool_orbit_meta.csv")
print("exported tool_env.csv rows=%d period_h=%.5f e=%.6f" % (len(env), o.period_s/3600, o.eccentricity))
print("apogee_alt_km=%.1f perigee_alt_km=%.1f" % (env.altitude_m.max()/1e3, env.altitude_m.min()/1e3))
