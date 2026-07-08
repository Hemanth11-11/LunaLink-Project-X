"""Independent SPICE + Orekit cross-check of the LunaLink tool.

Runs in the reference venv (numpy 2.2.6). Imports the tool's REAL analytic
Sun/Moon functions via PYTHONPATH so we validate the shipped code, not a copy.
Writes a markdown + CSV comparison artifact.
"""
import sys, math, json
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/hemanth/Downloads/Project X/code")
from lunalink.environment import (  # noqa: E402
    approximate_sun_hat_eci, approximate_moon_position_eci_m, parse_epoch_utc,
)

EPOCH = "2026-07-06T00:00:00Z"
env = pd.read_csv("/tmp/claude-1000/tool_env.csv")
_meta_raw = pd.read_csv("/tmp/claude-1000/tool_orbit_meta.csv", index_col=0).iloc[:, 0]
meta = {k: float(v) for k, v in _meta_raw.items() if k != "epoch_utc"}
meta = pd.Series(meta)
times = env["t_s"].to_numpy()
epoch_dt = parse_epoch_utc(EPOCH)
out = {}


def ang_deg(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    return math.degrees(math.acos(max(-1.0, min(1.0, float(np.dot(a, b))))))


# ---------------- SPICE: Sun/Moon ephemeris vs tool analytic ----------------
import spiceypy as sp  # noqa: E402
for k in ("naif0012.tls", "de440s.bsp", "pck00011.tpc"):
    sp.furnsh(f"/tmp/claude-1000/spice/{k}")
et0 = sp.str2et("2026-07-06T00:00:00")

sun_err, moon_err = [], []
for t in times:
    et = et0 + float(t)
    sun_spice = np.array(sp.spkpos("SUN", et, "J2000", "NONE", "EARTH")[0])
    moon_spice = np.array(sp.spkpos("MOON", et, "J2000", "NONE", "EARTH")[0])
    sun_tool = approximate_sun_hat_eci(epoch_dt, float(t))
    moon_tool = approximate_moon_position_eci_m(epoch_dt, float(t))
    sun_err.append(ang_deg(sun_tool, sun_spice))
    moon_err.append(ang_deg(moon_tool, moon_spice))
# Moon distance check (tool fixes 384,400 km)
moon_dist_spice_km = np.linalg.norm(sp.spkpos("MOON", et0, "J2000", "NONE", "EARTH")[0])
out["spice_sun_dir_err_deg_max"] = float(np.max(sun_err))
out["spice_sun_dir_err_deg_mean"] = float(np.mean(sun_err))
out["spice_moon_dir_err_deg_max"] = float(np.max(moon_err))
out["spice_moon_dir_err_deg_mean"] = float(np.mean(moon_err))
out["spice_moon_distance_km"] = float(moon_dist_spice_km)
out["tool_moon_distance_km"] = 384400.0
print("SPICE Sun dir err  max/mean deg: %.4f / %.4f" % (out["spice_sun_dir_err_deg_max"], out["spice_sun_dir_err_deg_mean"]))
print("SPICE Moon dir err max/mean deg: %.4f / %.4f" % (out["spice_moon_dir_err_deg_max"], out["spice_moon_dir_err_deg_mean"]))
print("SPICE Moon distance km: %.0f  (tool fixes 384400)" % moon_dist_spice_km)

# ---------------- Orekit: full-force propagation vs tool --------------------
try:
    import orekit_jpype
    orekit_jpype.initVM()
    from orekit_jpype.pyhelpers import setup_orekit_curdir
    setup_orekit_curdir("/tmp/claude-1000/orekit-data.zip")
    from org.orekit.time import AbsoluteDate, TimeScalesFactory
    from org.orekit.frames import FramesFactory
    from org.orekit.orbits import KeplerianOrbit, PositionAngleType, OrbitType
    from org.orekit.utils import IERSConventions
    from org.orekit.propagation import SpacecraftState
    from org.orekit.propagation.numerical import NumericalPropagator
    from org.hipparchus.ode.nonstiff import DormandPrince853Integrator
    from org.orekit.forces.gravity import HolmesFeatherstoneAttractionModel, ThirdBodyAttraction
    from org.orekit.forces.gravity.potential import GravityFieldFactory
    from org.orekit.bodies import CelestialBodyFactory

    utc = TimeScalesFactory.getUTC()
    eme2000 = FramesFactory.getEME2000()
    itrf = FramesFactory.getITRF(IERSConventions.IERS_2010, True)
    mu = float(meta["mu"])
    Re = float(meta["Re"])
    epoch = AbsoluteDate("2026-07-06T00:00:00.000", utc)

    def make_orbit(inc_rad):
        return KeplerianOrbit(float(meta["a_m"]), float(meta["e"]), float(inc_rad),
                              float(meta["argp_rad"]), float(meta["raan_rad"]),
                              float(meta["nu_rad"]), PositionAngleType.TRUE, eme2000, epoch, mu)

    orbit0 = make_orbit(float(meta["i_rad"]))
    out["orekit_period_s"] = float(orbit0.getKeplerianPeriod())
    out["tool_period_s"] = float(meta["period_s"])
    out["orekit_apogee_alt_km"] = (float(meta["a_m"]) * (1 + float(meta["e"])) - Re) / 1e3
    out["orekit_perigee_alt_km"] = (float(meta["a_m"]) * (1 - float(meta["e"])) - Re) / 1e3

    def build_prop(orbit, degree=8):
        minStep, maxStep, posTol = 1.0, 300.0, 1.0
        integ = DormandPrince853Integrator(minStep, maxStep, posTol, 1e-3)
        prop = NumericalPropagator(integ)
        prop.setOrbitType(OrbitType.CARTESIAN)
        prop.setInitialState(SpacecraftState(orbit))
        provider = GravityFieldFactory.getNormalizedProvider(degree, degree)
        prop.addForceModel(HolmesFeatherstoneAttractionModel(itrf, provider))
        prop.addForceModel(ThirdBodyAttraction(CelestialBodyFactory.getSun()))
        prop.addForceModel(ThirdBodyAttraction(CelestialBodyFactory.getMoon()))
        return prop

    # Position deviation tool (J2 only) vs Orekit (8x8 + luni-solar) over 36 h
    prop = build_prop(orbit0)
    pos_err_km = []
    for _, r in env.iterrows():
        st = prop.propagate(epoch.shiftedBy(float(r["t_s"])))
        pv = st.getPVCoordinates(eme2000).getPosition()
        ork = np.array([pv.getX(), pv.getY(), pv.getZ()])
        tool = np.array([r["x_eci_m"], r["y_eci_m"], r["z_eci_m"]])
        pos_err_km.append(np.linalg.norm(ork - tool) / 1e3)
    out["orekit_vs_tool_pos_err_km_max"] = float(np.max(pos_err_km))
    out["orekit_vs_tool_pos_err_km_rms"] = float(np.sqrt(np.mean(np.square(pos_err_km))))

    # Frozen apsides: argp drift over 30 days at 63.4 deg vs 45 deg
    def argp_drift_deg_per_day(inc_deg, days=30):
        orbit = make_orbit(math.radians(inc_deg))
        prop = build_prop(orbit)
        ts, argps = [], []
        for d in range(days + 1):
            st = prop.propagate(epoch.shiftedBy(float(d * 86400)))
            ko = KeplerianOrbit(st.getOrbit())
            ts.append(d)
            argps.append(math.degrees(ko.getPerigeeArgument()))
        argp_un = np.unwrap(np.radians(argps))
        slope = np.polyfit(ts, np.degrees(argp_un), 1)[0]
        return float(slope)

    out["orekit_argp_drift_deg_per_day_i63p4"] = argp_drift_deg_per_day(63.4)
    out["orekit_argp_drift_deg_per_day_i45"] = argp_drift_deg_per_day(45.0)
    print("Orekit period s: %.2f (tool %.2f)" % (out["orekit_period_s"], out["tool_period_s"]))
    print("Orekit vs tool pos err km  max/rms: %.2f / %.2f" % (out["orekit_vs_tool_pos_err_km_max"], out["orekit_vs_tool_pos_err_km_rms"]))
    print("Orekit argp drift deg/day  i=63.4: %.4f   i=45: %.4f" % (out["orekit_argp_drift_deg_per_day_i63p4"], out["orekit_argp_drift_deg_per_day_i45"]))
    out["orekit_available"] = True
except Exception as e:
    import traceback; traceback.print_exc()
    out["orekit_available"] = False
    out["orekit_error"] = str(e)

json.dump(out, open("/tmp/claude-1000/refcheck_results.json", "w"), indent=2)
print("\nWROTE /tmp/claude-1000/refcheck_results.json")
