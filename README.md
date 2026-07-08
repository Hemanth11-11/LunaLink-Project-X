# LunaLink Engineering Simulator

LunaLink is a preliminary Python mission-analysis tool for the Project X brief.
It models the fixed 500 x 36,000 km, 63.4 deg Earth orbit and all four selected
subsystems: EPS, TCS, ADCS, and TT&C.

This tool is NASA/ECSS-inspired, not flight-qualified. Flight qualification would
require formal IV&V, independent model correlation, configuration-controlled
requirements, and authority acceptance.

## Quick Start

Create the Python 3.13 environment:

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r code/requirements.txt
```

Run the simulator and checks:

```bash
.venv/bin/python code/main_simulation.py --quick --out outputs/ci
.venv/bin/python report/build_report.py --evidence outputs/ci --out report/LunaLink_Report_Draft.md
MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q
.venv/bin/ruff check code
```

Interactive dashboard:

```bash
.venv/bin/streamlit run code/main_gui.py
```

The dashboard opens on a mission **Home** screen (hero, verification KPIs, a live
3D globe, and a subsystem status board) and gives every subsystem its own tab
(**Orbit & Environment, EPS, TCS, ADCS, TT&C, Evidence**). The 3D scenes use a
texture-mapped, sun-shaded Earth and Moon (real NASA-derived equirectangular
maps in `assets/textures/`) and a multi-material spacecraft driven by the ADCS
attitude quaternion. Heavy 3D rendering lives in `code/viz3d.py`; the headless
`code/main_simulation.py` never imports it.

## Outputs

- `outputs/ci/*_timeseries.csv`: mission and subsystem time histories.
- `outputs/ci/validation_metrics.csv`: pass/warn/fail checks.
- `outputs/ci/trade_results.csv`: EPS array/battery sizing trade.
- `outputs/ci/lhs_samples.csv`: Latin Hypercube design samples.
- `outputs/ci/monte_carlo_samples.csv`: Monte Carlo design samples.
- `outputs/ci/formula_traceability.csv`: requirement/formula/reference/test traceability.
- `outputs/ci/figures/*.png`: engineering figures and one Pareto-style trade plot.
- `outputs/ci/scenario_exports/*`: GMAT/Orekit-style scenario seeds and validation recipe.
- `report/LunaLink_Report_Draft.md`: generated report from the evidence bundle.

## Baseline Mission

- Orbit: 500 x 36,000 km altitude, inclination 63.4 deg.
- Period: about 10.6845 h from the fixed altitudes.
- Simulation duration: at least 36 h.
- Spacecraft mass: 500 kg.
- EOL power budget: 1.2 kW.
- Earth downlink: X-band, at least 100 Mbps in contact.
- Moon link: UHF 400-512 MHz class low-rate link.
- Ground station: Ottobrunn, 48.07 deg N, 11.65 deg E, minimum elevation 5 deg.

## Engineering Notes

The simulator uses SI internally and intentionally favors transparent equations
over hidden black-box behavior. It includes WGS84 ground geometry, numerical
J2 propagation, explicit EPS array incidence modes, mixed-coating thermal
surfaces, full Euler ADCS rate dynamics, and expanded RF link-budget evidence.
The current dynamics are suitable for early engineering trade studies, not
operations or flight certification.

## High-fidelity extensions (validated against reference tools)

- **Orbit** (`orbit_analysis.py`): luni-solar third-body + J3 perturbations, the
  63.4 deg critical-inclination frozen-apsides demonstration, and a
  station-keeping delta-v estimate. Cross-checked against **Orekit 13.1** and
  **NASA SPICE/DE440** (`outputs/baseline/external_validation/`).
- **Radiation** (`radiation.py`): McIlwain L-shell belt exposure, annual dose,
  and 1 MeV-equivalent solar-array degradation over the 5-year life.
- **ADCS** (`adcs.py::run_sun_pointing`, `magnetic_field.py`): closed-loop PD
  sun-pointing with real pointing error, plus an IGRF-14 vs dipole field
  cross-check (optional `ppigrf`).
- **TT&C** (`comms_atmosphere.py`): ITU-R P.618/P.676 elevation-dependent rain +
  gas attenuation (optional `itur`), CCSDS coding gain, and Doppler.

The heavy reference tools (Orekit/SPICE) are run offline; `ppigrf` and `itur`
are optional and degrade gracefully, so the tool still installs and runs with a
plain `pip install -r code/requirements.txt` and one command.
