"""Physical constants used by the LunaLink simulator.

Internal units are SI unless a symbol explicitly states otherwise.
"""

from __future__ import annotations

import math

EARTH_MU_M3_S2 = 3.986004418e14
EARTH_RADIUS_M = 6_378_137.0
EARTH_FLATTENING = 1.0 / 298.257223563
EARTH_J2 = 1.08262668e-3
EARTH_J3 = -2.53265649e-6
EARTH_ROT_RATE_RAD_S = 7.2921150e-5
EARTH_EQUATORIAL_B_T = 3.12e-5

# Third-body gravitational parameters and mean Moon distance (SI).
SUN_MU_M3_S2 = 1.32712440018e20
MOON_MU_M3_S2 = 4.9028000661e12
MOON_MEAN_DISTANCE_M = 384_400_000.0
ASTRONOMICAL_UNIT_M = 1.495978707e11

SPEED_OF_LIGHT_M_S = 299_792_458.0
SOLAR_CONSTANT_W_M2 = 1361.0
STEFAN_BOLTZMANN_W_M2_K4 = 5.670374419e-8

STANDARD_GRAVITY_M_S2 = 9.80665

DEG2RAD = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
