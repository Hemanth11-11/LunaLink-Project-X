import numpy as np
import pandas as pd
from lunalink.trades import eps_pareto_grid, latin_hypercube_samples, monte_carlo_samples


def test_latin_hypercube_samples_are_reproducible_and_bounded():
    bounds = {"x": (0.0, 1.0), "y": (10.0, 20.0)}

    first = latin_hypercube_samples(bounds, n_samples=8, seed=7)
    second = latin_hypercube_samples(bounds, n_samples=8, seed=7)

    assert first.equals(second)
    assert first["x"].between(0.0, 1.0).all()
    assert first["y"].between(10.0, 20.0).all()


def test_monte_carlo_samples_are_reproducible_and_bounded():
    bounds = {"efficiency": (0.25, 0.32)}

    first = monte_carlo_samples(bounds, n_samples=5, seed=3)
    second = monte_carlo_samples(bounds, n_samples=5, seed=3)

    assert first.equals(second)
    assert first["efficiency"].between(0.25, 0.32).all()


def test_eps_pareto_grid_returns_expected_rows():
    environment = pd.DataFrame(
        {
            "t_s": np.array([0.0, 60.0, 120.0]),
            "eclipse_flag": np.array([False, True, False]),
            "solar_flux_w_m2": np.array([1361.0, 0.0, 1361.0]),
            "sun_hat_x": np.array([1.0, 1.0, 1.0]),
            "sun_hat_y": np.array([0.0, 0.0, 0.0]),
            "sun_hat_z": np.array([0.0, 0.0, 0.0]),
            "gs_contact_flag": np.array([False, False, False]),
        }
    )

    trade = eps_pareto_grid([4.0, 6.0], [3.0, 4.5], environment)

    assert len(trade) == 4
    assert trade["min_soc"].between(0.0, 1.0).all()

