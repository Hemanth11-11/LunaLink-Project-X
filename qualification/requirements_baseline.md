# Requirements Baseline

This baseline maps the Project X LunaLink brief to implemented evidence.

| ID | Requirement | Implementation | Evidence |
| --- | --- | --- | --- |
| REQ-MIS-001 | Simulate fixed 500 x 36,000 km, 63.4 deg orbit. | `lunalink.config`, `lunalink.orbit`, `lunalink.environment` | `mission_timeseries.csv`, validation metric `fixed_altitude_orbit_period_h` |
| REQ-MIS-002 | Simulate at least 36 h. | `SimulationConfig.duration_s` | validation metric `simulation_duration_h` |
| REQ-MIS-003 | Use Ottobrunn ground station at 5 deg minimum elevation. | `GroundStationConfig`, `frames.py` | `minimum_contact_elevation_rad` |
| REQ-EPS-001 | Model solar array, load, battery SOC, eclipse behavior, and 1.2 kW EOL power closure. | `lunalink.eps`, `lunalink.validation` | `eps_timeseries.csv`, EPS validation metrics |
| REQ-TCS-001 | Model thermal response with dynamic face fluxes, mixed coatings, and component limit flags. | `lunalink.thermal` | `thermal_timeseries.csv`, thermal summary |
| REQ-TCS-002 | Record worst hot/cold preliminary operating margin and target at least 5 K baseline margin. | `lunalink.thermal`, `lunalink.validation` | `thermal_worst_operating_margin_k` |
| REQ-ADCS-001 | Model detumble, full Euler rate dynamics, disturbance torques, and preliminary wheel momentum bookkeeping. | `lunalink.adcs` | `adcs_timeseries.csv`, ADCS summary |
| REQ-TTC-001 | Model X-band Earth downlink and UHF Moon-link screening budgets with RF evidence columns. | `lunalink.ttc` | `ttc_timeseries.csv`, TT&C summary |
| REQ-TTC-002 | Report Earth contact windows with sampled flags and refined 5 deg elevation crossings. | `lunalink.ttc` | TT&C summary, dashboard TT&C tab |
| REQ-TRADE-001 | Provide Monte Carlo and Latin Hypercube sampling helpers. | `lunalink.trades` | `lhs_samples.csv`, `monte_carlo_samples.csv` |
| REQ-TRADE-002 | Provide at least one Pareto-style trade plot. | `lunalink.trades`, `lunalink.plotting` | `trade_results.csv`, `pareto_eps_trade.png` |
| REQ-EVID-001 | Generate a repeatable evidence bundle. | `main_simulation.py`, `lunalink.io` | `outputs/<run>/` |
| REQ-EVID-002 | Generate a draft engineering report. | `lunalink.reporting` | `report/LunaLink_Report_Draft.md` |
| REQ-XCHK-001 | Export scenario seeds for external GMAT/Orekit comparison. | `lunalink.exporters` | `scenario_exports/` |

Open item: formal numerical cross-correlation against installed GMAT/Orekit is
planned, but not yet claimed as complete.
