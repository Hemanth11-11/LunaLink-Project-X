"""Lightweight uncertainty and design-trade helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from .eps import EpsConfig, run_eps


def latin_hypercube_samples(
    bounds: Mapping[str, tuple[float, float]], n_samples: int, seed: int = 42
) -> pd.DataFrame:
    """Generate reproducible Latin Hypercube samples within parameter bounds."""

    if n_samples <= 0:
        raise ValueError("n_samples must be positive.")
    rng = np.random.default_rng(seed)
    columns: dict[str, np.ndarray] = {}
    for name, (lower, upper) in bounds.items():
        if upper < lower:
            raise ValueError(f"Upper bound is below lower bound for {name}.")
        centers = (np.arange(n_samples, dtype=float) + rng.random(n_samples)) / n_samples
        rng.shuffle(centers)
        columns[name] = lower + centers * (upper - lower)
    return pd.DataFrame(columns)


def monte_carlo_samples(
    bounds: Mapping[str, tuple[float, float]], n_samples: int, seed: int = 42
) -> pd.DataFrame:
    """Generate reproducible uniform Monte Carlo samples within parameter bounds."""

    if n_samples <= 0:
        raise ValueError("n_samples must be positive.")
    rng = np.random.default_rng(seed)
    columns: dict[str, np.ndarray] = {}
    for name, (lower, upper) in bounds.items():
        if upper < lower:
            raise ValueError(f"Upper bound is below lower bound for {name}.")
        columns[name] = rng.uniform(lower, upper, size=n_samples)
    return pd.DataFrame(columns)


def eps_pareto_grid(
    array_areas_m2: Sequence[float],
    battery_capacities_kwh: Sequence[float],
    environment_df: pd.DataFrame,
) -> pd.DataFrame:
    """Evaluate an EPS sizing grid for the selected mission environment."""

    rows: list[dict[str, float]] = []
    for array_area_m2 in array_areas_m2:
        for battery_capacity_kwh in battery_capacities_kwh:
            config = EpsConfig(
                array_area_m2=float(array_area_m2),
                battery_capacity_kwh=float(battery_capacity_kwh),
            )
            _, summary = run_eps(environment_df, config)
            rows.append(
                {
                    "array_area_m2": float(array_area_m2),
                    "battery_capacity_kwh": float(battery_capacity_kwh),
                    "min_soc": float(summary["min_soc"]),
                    "final_soc": float(summary["final_soc"]),
                    "unserved_energy_j": float(summary["unserved_energy_j"]),
                    "curtailed_energy_j": float(summary["curtailed_energy_j"]),
                }
            )
    return pd.DataFrame(rows)

