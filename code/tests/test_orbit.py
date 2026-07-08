import numpy as np
from lunalink.config import MissionConfig, SimulationConfig, default_mission_config
from lunalink.constants import EARTH_MU_M3_S2
from lunalink.orbit import orbital_elements_to_state, propagate_orbit, specific_energy


def test_initial_orbit_state_starts_at_perigee():
    config = default_mission_config()
    state = orbital_elements_to_state(config.orbit)

    radius_m = np.linalg.norm(state.r_eci_m)
    speed_mps = np.linalg.norm(state.v_eci_mps)
    expected_speed_mps = np.sqrt(
        EARTH_MU_M3_S2
        * (2.0 / config.orbit.perigee_radius_m - 1.0 / config.orbit.semi_major_axis_m)
    )

    assert abs(radius_m - config.orbit.perigee_radius_m) < 1e-6
    assert abs(speed_mps - expected_speed_mps) < 1e-9


def test_two_body_energy_is_stable_over_one_orbit():
    base = default_mission_config()
    config = MissionConfig(
        simulation=SimulationConfig(duration_s=base.orbit.period_s, output_step_s=120.0)
    )
    states = propagate_orbit(config, include_j2=False)

    energies = []
    for row in states.itertuples(index=False):
        r = np.array([row.x_eci_m, row.y_eci_m, row.z_eci_m], dtype=float)
        v = np.array([row.vx_eci_mps, row.vy_eci_mps, row.vz_eci_mps], dtype=float)
        energies.append(specific_energy(r, v))

    relative_drift = (max(energies) - min(energies)) / abs(energies[0])
    assert relative_drift < 1e-7


def test_phase2_propagation_covers_required_duration():
    config = default_mission_config()
    states = propagate_orbit(config, include_j2=True)

    assert states["t_s"].iloc[-1] >= 36.0 * 3600.0
    assert states["altitude_m"].min() > 450_000.0
    assert states["altitude_m"].max() < 36_500_000.0
