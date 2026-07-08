# LunaLink Final 10/10 Execution Plan

Date: 2026-07-07
Role framing: NASA-style systems engineer, spacecraft subsystem engineer, and Python tool architect.
Project folder: `/home/godspeed/Downloads/Project X`

This is the final build plan for a high-scoring LunaLink mission engineering simulator. It consolidates:

- `ProjectX_LunaLink_Brief_v2.pdf`
- `LunaLink_AllSubsystems_Professional_Plan.md`
- `LunaLink_Engineering_Grade_Integrated_Architecture.md`
- The subsystem specialist reviews
- The optimization scope discussion

The plan is deliberately ambitious but bounded. A 10/10 academic engineering tool is possible. A true flight-qualified simulator is not the claim.

## 1. Final Position

We will build a Python-based LunaLink mission engineering workbench.

It will include:

- Orbit and environment simulation
- EPS simulation and sizing
- Thermal control simulation
- ADCS simulation
- TT&C simulation
- GUI visualization
- Headless evidence generation
- Validation metrics
- References and formulas traceable to credible aerospace sources

The PDF asks for one subsystem. The user selected all four, so the project exceeds the assignment scope while still satisfying every original requirement.

## 2. Definition of 10/10

A 10/10 tool for this project means:

1. It runs first time from clean instructions.
2. It simulates at least 36 hours and at least 3 actual orbits.
3. It uses the fixed mission parameters from the brief.
4. It openly resolves the orbit-period inconsistency.
5. It uses one shared orbit/environment truth table.
6. All four subsystems consume the same physics state.
7. Every major formula is documented and cited.
8. Every major output has a validation check.
9. The GUI is useful, not decorative.
10. The report can be generated from reproducible evidence files.

The correct professional claim is:

```text
This is a validated medium-fidelity academic mission engineering simulator.
It is not flight-qualified software.
```

## 3. Core Mission Assumptions

Fixed brief parameters:

```text
orbit type: HEO, Molniya-type
perigee altitude: 500 km
apogee altitude: 36,000 km
inclination: 63.4 deg
spacecraft mass: 500 kg
EOL power budget: 1.2 kW
design lifetime: at least 5 years
Earth downlink: X-band, at least 100 Mbps
Moon uplink: UHF, 400-512 MHz
envelope: 2.0 x 1.5 x 1.0 m
ground station: Ottobrunn, Germany, 48.07 N, 11.65 E
minimum elevation: 5 deg
```

Important correction:

```text
500 x 36,000 km does not produce a 12 hour period.
It produces about 10.6845 hours.
```

Baseline decision:

- Use the fixed altitudes from the brief.
- Compute and display the real period.
- Simulate at least 36 hours.
- State that 36 hours covers about 3.37 fixed-altitude orbits.
- Optional sensitivity: exact 12 hour orbit with about 39,964 km apogee altitude.

## 4. Scope Boundary

### In Scope

- Orbit propagation with central gravity and J2.
- Ground station contact windows.
- Eclipse geometry.
- Sun and Moon geometry.
- EPS energy balance and sizing.
- Thermal lumped-parameter model.
- ADCS detumbling and pointing modes.
- TT&C link budgets and data volume.
- GUI visualization.
- Validation metrics.
- Evidence bundle for report.
- Monte Carlo/sensitivity analysis.
- One constrained design optimizer if time allows.

### Out of Scope

- Full trajectory optimization.
- Launch window optimization.
- Low-thrust transfer design.
- Orbit determination.
- Full finite-element thermal modeling.
- High-fidelity flexible-body ADCS.
- Flight software certification.
- Implementing a large optimizer zoo.

Reason:

The orbit is fixed by the brief. Optimization should improve subsystem sizing and robustness, not replace the mission task.

## 5. Optimization Decision

The listed algorithms are real and useful:

- Differential Evolution
- self-adaptive DE
- PSO
- genetic algorithms
- NSGA-II
- SPEA2
- simulated annealing
- covariance matrix adaptation
- Monte Carlo search
- basin hopping
- multistart
- SLSQP
- BFGS
- Nelder-Mead
- others

But most are not needed for a 10/10 LunaLink submission.

Final optimization scope:

1. Monte Carlo / sensitivity analysis: include.
2. SciPy Differential Evolution or SLSQP design optimizer: optional but recommended.
3. Multi-objective optimizer such as NSGA-II: stretch only.
4. Full trajectory optimization: exclude.

Recommended optimizer uses:

- Minimize solar array area while maintaining SOC margin.
- Minimize battery capacity while respecting DoD.
- Choose antenna diameter and transmitter power for at least 3 dB link margin.
- Explore coating choices against temperature limits.
- Show trade curves, not algorithm comparisons.

This gives engineering value without distracting from the PDF requirements.

## 6. Architecture

Use a library-first layout:

```text
code/
  main_simulation.py
  main_gui.py
  requirements.txt
  lunalink/
    __init__.py
    constants.py
    config.py
    orbit.py
    frames.py
    environment.py
    eps.py
    thermal.py
    adcs.py
    ttc.py
    trades.py
    simulation.py
    validation.py
    plotting.py
    io.py
  tests/
    test_orbit.py
    test_frames.py
    test_environment.py
    test_eps.py
    test_thermal.py
    test_adcs.py
    test_ttc.py
    test_trades.py
report/
outputs/
README.txt
```

Rules:

- Internal units are SI.
- No Streamlit imports inside physics modules.
- No plotting inside physics modules.
- `main_simulation.py` is the authoritative evidence generator.
- `main_gui.py` is only a visualization and interaction layer.
- All assumptions live in `MissionConfig`.
- Every module returns structured results.

## 7. Shared Mission Truth Table

The orbit/environment module produces one time-indexed table:

```text
time_utc
r_eci_m, v_eci_mps
r_ecef_m
lat_rad, lon_rad, alt_m
true_anomaly_rad
sun_hat_eci
moon_hat_eci
eclipse_flag
solar_flux_w_m2
gs_range_m
gs_elevation_rad
gs_azimuth_rad
gs_contact_flag
moon_range_m
moon_occulted_flag
earth_ir_flux_w_m2
albedo_flux_w_m2
magnetic_field_eci_t
atmospheric_density_kg_m3
face_normals_eci
```

This is the backbone. EPS, TCS, ADCS, and TT&C must not invent separate geometry.

## 8. Subsystem Build Plan

### 8.1 Orbit and Environment

Model:

- Central Earth gravity.
- J2 perturbation.
- ECI/ECEF/topocentric frames.
- Ground station contact.
- Eclipse.
- Sun/Moon vectors.
- Simplified magnetic field and atmospheric density.

Validation:

- Period equals about 10.6845 h.
- Perigee/apogee match 500 km and 36,000 km.
- Simulation duration is at least 36 h.
- Ground contact never occurs below 5 deg elevation.
- Eclipse flag is geometrically consistent.

### 8.2 EPS

Model:

- Deployable triple-junction solar array.
- Battery SOC and energy balance.
- Safe, nominal, and peak relay modes.
- TT&C load coupling.
- Heater load coupling.
- Optional thermal derating.

Baseline:

```text
solar array area: 6.0 m^2
battery capacity: 4.0-4.5 kWh
safe load: 250-350 W
nominal load: 750-950 W
peak load: 1100-1200 W
```

Validation:

- Eclipse discharges battery.
- Sunlight recharges battery.
- Energy balance closes.
- SOC remains 0-100 percent.
- Warnings appear below SOC margin.

### 8.3 Thermal Control

Model:

- Six external face nodes.
- One internal equipment node.
- Direct solar, albedo, Earth IR, deep-space radiation.
- MLI-like insulated faces.
- Explicit radiator faces.
- Hot/cold case flags.

Validation:

- Face areas sum to 13 m^2.
- White paint cooler than black paint in Sun.
- OSR/FEP radiator runs coolest in direct Sun.
- Internal dissipation raises internal temperature.
- Component limits trigger correctly.

### 8.4 ADCS

Model:

- Rigid-body attitude dynamics.
- Quaternion or DCM propagation.
- B-dot detumbling.
- Reaction wheel pointing.
- Perigee-weighted magnetic desaturation.
- Gravity-gradient, SRP, drag, residual magnetic disturbance torques.

Baseline:

```text
Ixx = 135.4 kg m^2
Iyy = 208.3 kg m^2
Izz = 260.4 kg m^2
initial tumble = 10 deg/s
magnetorquers = +/-300 to +/-500 A m^2
reaction wheels = 0.05-0.10 Nm, 8-20 Nms
```

Validation:

- Quaternion norm stays near 1.
- B-dot reduces tumble below threshold.
- Magnetorquer torque is perpendicular to B.
- SRP torque vanishes in eclipse.
- Wheel momentum and desaturation behavior are visible.

### 8.5 TT&C

Model:

- Earth X-band downlink.
- Moon UHF link.
- Contact windows.
- Link budget.
- Data volume.
- ADCS pointing loss coupling.
- EPS power availability coupling.

Baseline:

```text
Earth downlink: 8.4 GHz, 100 Mbps
spacecraft HGA: 0.6 m, about 32 dBi
ground dish: 3.0 m, about 46 dBi
Moon UHF: 450 MHz, 1-10 kbps default
required final margin: at least 3 dB
```

Validation:

- FSPL doubles range -> about +6 dB.
- FSPL increases 10x frequency -> about +20 dB.
- Accepted links have at least 3 dB margin.
- Data volume equals rate times contact duration times efficiency.

## 9. Design Trades Tab

Add a GUI tab called `Design Trades`.

Minimum version:

- Sensitivity sliders.
- Monte Carlo uncertainty bands.
- EPS sizing sweep.
- TT&C link margin sweep.

Optional version:

- Constrained optimizer using SciPy Differential Evolution or SLSQP.
- Objective examples:
  - minimize array area
  - minimize battery capacity
  - minimize RF power
  - maximize data return
  - maintain all constraints

Do not compare many algorithms. The project is not an optimization-methods paper.

## 10. GUI Plan

Use Streamlit and Plotly.

Tabs:

1. Mission Overview
2. Orbit and Contacts
3. EPS
4. Thermal
5. ADCS
6. TT&C
7. Design Trades
8. Assumptions and Validation

The GUI must show:

- Orbit period and orbit ambiguity warning.
- Ground track.
- Eclipse/contact timeline.
- EPS power and SOC.
- Thermal face and internal temperatures.
- ADCS attitude/pointing/wheel plots.
- TT&C link margin and data volume.
- Pass/warn/fail validation table.

## 11. Evidence Bundle

The headless run writes:

```text
outputs/baseline/
  run_manifest.json
  assumptions.json
  validation_metrics.csv
  mission_timeseries.csv
  eps_summary.csv
  thermal_summary.csv
  adcs_summary.csv
  ttc_link_budget.csv
  contact_windows.csv
  trade_results.csv
  figures/
    orbit_groundtrack.png
    eclipse_contact_timeline.png
    eps_power_soc.png
    thermal_faces_internal.png
    adcs_detumble_pointing.png
    adcs_torques_wheel_momentum.png
    ttc_range_margin_data.png
```

The report uses these files only. No hand-edited result numbers.

## 12. Build Phases and Verification Gates

Phase 1: scaffold and configuration

- Build folder structure, requirements, config dataclasses.
- Verify: imports and tests discover correctly.

Phase 2: orbit/environment core

- Implement propagation, frames, eclipse, contacts.
- Verify: orbit and geometry tests pass.

Phase 3: EPS and TT&C

- Implement energy balance and link budget.
- Verify: SOC and link margin tests pass.

Phase 4: thermal

- Implement seven-node thermal model.
- Verify: coating and heat-balance tests pass.

Phase 5: ADCS

- Implement simplified but honest ADCS.
- Verify: quaternion, detumble, and torque tests pass.

Phase 6: design trades

- Implement Monte Carlo and optional constrained optimizer.
- Verify: trades run reproducibly with fixed random seed.

Phase 7: GUI

- Implement Streamlit/Plotly interface.
- Verify: GUI imports and launches; no physics inside GUI.

Phase 8: report assets and README

- Generate evidence bundle and instructions.
- Verify: clean command sequence works.

## 13. Reference Foundation

Use these as technical anchors:

### Systems and Software Engineering

- NASA Systems Engineering Handbook
- NASA Software Engineering Handbook / NASA-HDBK-2203
- NASA NPR 7150.2D software engineering requirements
- NASA-STD-8739.8B software assurance and software safety
- ECSS-E-ST-10 system engineering
- ECSS-E-ST-10-02 verification
- ECSS-Q-ST-80 software product assurance
- ECSS-S-ST-00 ECSS system description, implementation, and general requirements
- ECSS active standards list and applicability/tailoring material from the ECSS website
- ECSS-style tailoring: use traceability, verification evidence, interfaces, assumptions, and configuration control without claiming formal compliance

### Astrodynamics and Orbit

- Vallado, `Fundamentals of Astrodynamics and Applications`
- Curtis, `Orbital Mechanics for Engineering Students`
- GMAT documentation and V&V style
- Orekit documentation for frames, dates, propagation, events, and attitudes
- NAIF/SPICE documentation for observation geometry discipline
- Tudat documentation for high-fidelity astrodynamics inspiration

### Spacecraft Subsystems

- Wertz and Larson, `Space Mission Analysis and Design`
- Fortescue, Stark, and Swinerd, `Spacecraft Systems Engineering`
- NASA Small Spacecraft Technology State-of-the-Art

### EPS

- SMAD spacecraft power sizing methods
- NASA SmallSat SoA power chapter
- Manufacturer-style solar array and Li-ion battery assumptions where cited
- ECSS-E-ST-20 electrical and electronic engineering as an engineering-practice reference

### Thermal

- Gilmore, `Spacecraft Thermal Control Handbook`
- Lumped-parameter radiative heat balance references
- NASA SmallSat SoA thermal control chapter
- ECSS-E-ST-31 thermal control as an engineering-practice reference

### ADCS

- Wertz, `Spacecraft Attitude Determination and Control`
- Sidi, `Spacecraft Dynamics and Control`
- B-dot detumbling literature
- Basilisk architecture references
- ECSS-E-ST-60 control engineering as an engineering-practice reference

### TT&C

- Maral and Bousquet, `Satellite Communications Systems`
- CCSDS RF and modulation references
- ITU Earth-space propagation references
- NASA SmallSat SoA communications chapter
- ECSS-E-ST-50 communications as an engineering-practice reference

### Optimization

- Storn and Price, Differential Evolution
- SciPy `differential_evolution`
- Biscani and Izzo, pagmo/pygmo
- Monte Carlo and Latin Hypercube uncertainty analysis references

## 14. Confidence Improvements Before Coding

To raise confidence toward 10/10:

1. Keep the first build simple and complete.
2. Add validation tests before polishing GUI details.
3. Use SI internally from day one.
4. Generate evidence files automatically.
5. Make all warnings visible.
6. Include a references/formulas table in the report.
7. Avoid full trajectory optimization.
8. Include Monte Carlo only after deterministic baseline passes.
9. Keep optimizer as a trade tool, not the main story.
10. Make README commands boring and reliable.

## 15. Added 10/10 Professionalization Improvements

These improvements are now part of the execution plan. They are the difference between a strong class project and a tool that looks like it was built with professional engineering discipline.

### 15.1 Requirements Traceability Matrix

Create `outputs/baseline/requirements_traceability.csv`.

Each row maps:

```text
requirement_id
pdf_requirement
interpretation
module
output_artifact
validation_metric
report_section
status
```

Minimum requirement IDs:

```text
REQ-ORB-001: simulate at least 36 h / at least 3 orbits
REQ-ORB-002: use fixed LunaLink orbit parameters
REQ-GUI-001: provide interactive GUI with adjustable parameters
REQ-EPS-001: solar array and battery sizing
REQ-TCS-001: surface and internal temperature time series
REQ-ADCS-001: detumbling and pointing simulation
REQ-TTC-001: Earth/Moon contact windows and link budgets
REQ-REP-001: assumptions, results, AI use, references
REQ-RUN-001: clean pip install and one-command run
```

This makes the project hard to mark down because every PDF demand has evidence.

### 15.2 Formula and Reference Register

Create `outputs/baseline/formula_register.csv`.

Each row maps:

```text
formula_id
equation_name
equation_text
variables
source
module
test_name
```

Required formula groups:

- Kepler period and orbital elements.
- J2 acceleration.
- ECI/ECEF/topocentric conversion.
- Eclipse geometry.
- Solar array power.
- Battery energy balance.
- Thermal lumped-node heat balance.
- Gravity-gradient torque.
- B-dot detumbling law.
- Reaction wheel momentum balance.
- Antenna gain.
- Free-space path loss.
- C/N0, Eb/N0, and link margin.
- Data volume integration.

### 15.3 Validation Dashboard

The GUI must include a validation tab with pass/warn/fail status.

Minimum checks:

```text
orbit period: expected about 10.6845 h
perigee/apogee: expected 500 km and 36,000 km
duration: at least 36 h
contacts: no contact below 5 deg elevation
EPS: energy residual within tolerance
EPS: SOC remains in physical bounds
TCS: all temperatures remain positive Kelvin
TCS: component operating/survival limits flagged
ADCS: quaternion norm remains near 1
ADCS: detumble threshold reached or warning shown
TT&C: accepted links have at least 3 dB margin
TT&C: data volume matches integrated rate
```

### 15.4 Independent Sanity Checks

The report and validation output should include a small hand-check table:

```text
fixed-altitude orbit period: about 10.6845 h
orbits in 36 h: about 3.37
box inertia: about 135 / 208 / 260 kg m^2
solar array order of magnitude: about 5-6 m^2
battery capacity order of magnitude: about 4 kWh
X-band FSPL at 42,000 km: about 203 dB
UHF lunar FSPL near 384,400 km: about 197 dB
Earth view factor near perigee: about 0.86 for nadir face
Earth view factor near apogee: about 0.023 for nadir face
```

### 15.5 Uncertainty and Sensitivity

Add a controlled Monte Carlo mode after deterministic baseline passes.

Vary:

- Solar efficiency and degradation.
- Battery capacity and DoD.
- Payload/relay duty cycle.
- Coating absorptivity and emissivity.
- Internal dissipation.
- Antenna gains.
- Pointing losses.
- Atmospheric density multiplier.
- Residual magnetic dipole.

Use fixed random seed for reproducibility. Output:

```text
monte_carlo_summary.csv
monte_carlo_envelopes.png
```

### 15.6 Constraint and Margin Ledger

Create `outputs/baseline/margins.csv`.

Track:

```text
power margin
SOC margin
battery DoD margin
thermal hot/cold margin
link margin
pointing margin
reaction wheel momentum margin
magnetorquer authority warning
```

This is more professional than just saying "it works."

### 15.7 Interface Control Table

Create `docs/Interface_Control_Table.md` or include it in the report appendix.

Each subsystem interface states:

```text
producer module
consumer module
variable name
units
shape
frame
sign convention
valid range
```

This prevents the classic simulation failure: correct formulas connected with wrong units or wrong frames.

### 15.8 Model Credibility Levels

Assign each model a credibility label:

```text
MCL-1: hand equation only
MCL-2: unit-tested implementation
MCL-3: integrated with mission time series
MCL-4: validated against independent check or reference tool
MCL-5: flight/mission qualified
```

For this project, target MCL-3 for all subsystems and MCL-4 for orbit/contact/link-budget sanity checks. Do not claim MCL-5.

### 15.9 Industry-Readiness Practices

Add these lightweight professional practices:

- Scenario versioning in `run_manifest.json`.
- Fixed random seeds for trades.
- Regression baseline outputs.
- Clear assumptions JSON.
- Type hints in core modules.
- Unit tests for formulas.
- Integration tests for a quick run.
- No network dependency at runtime.
- No hidden GUI-only physics.
- Explicit limitations in README and report.

This makes the tool credible as a preliminary design and teaching workbench. It still should not be presented as an operational flight product.

### 15.10 Remaining Optional Improvements

These are useful but not mandatory for 10/10:

- Independent comparison of orbit/contact outputs against GMAT or Orekit.
- Export a simple GMAT/Orekit-style scenario description.
- Add Latin Hypercube sampling in addition to simple Monte Carlo.
- Add one Pareto trade plot for EPS mass/area vs margin.
- Add a report auto-builder if time remains.
- Add static checks such as `ruff` after the main tool works.

Do not add these until the deterministic simulator, validation dashboard, GUI, and evidence bundle are complete.

### 15.11 Accepted Stretch Upgrades

The following upgrades are now accepted into the plan as stretch deliverables. They should be implemented after the deterministic simulator passes validation.

#### GMAT / Orekit Comparison

Purpose:

- Increase trust in orbit and contact-window outputs.
- Show that the in-house Python propagator is not drifting into an obviously wrong regime.

Implementation:

- Export a GMAT-style scenario file or a simplified scenario description.
- Export an Orekit-style JSON/YAML scenario description.
- Generate comparison tables for:
  - period
  - perigee/apogee
  - ground-station contact start/end
  - max elevation
  - eclipse intervals

Runtime rule:

- GMAT and Orekit remain optional validators.
- The submitted Python tool must not require them to run.

Output:

```text
outputs/baseline/external_validation/
  gmat_scenario.script
  orekit_scenario.json
  orbit_contact_comparison.csv
  external_validation_notes.md
```

#### Latin Hypercube Sampling

Purpose:

- Improve uncertainty coverage beyond plain random Monte Carlo.

Implementation:

- Add a reproducible Latin Hypercube sampler in `trades.py`.
- Use fixed random seed.
- Sample the same uncertainty variables used by Monte Carlo.
- Compare LHS envelopes against Monte Carlo envelopes.

Output:

```text
outputs/baseline/lhs_summary.csv
outputs/baseline/figures/lhs_uncertainty_envelopes.png
```

#### Pareto Trade Plot

Purpose:

- Show professional design-trade thinking without turning the project into an optimization thesis.

Recommended Pareto plots:

- EPS: solar array area vs battery capacity vs minimum SOC margin.
- TT&C: antenna diameter / RF power vs link margin and data volume.

Minimum implementation:

- One Pareto plot is enough.
- Use a small grid or constrained optimizer results.
- Highlight the selected baseline design.

Output:

```text
outputs/baseline/pareto_trade.csv
outputs/baseline/figures/pareto_eps_trade.png
```

#### Static Checks

Purpose:

- Raise software quality and make the project easier to trust.

Implementation:

- Add `ruff` to development checks.
- Keep it lightweight: lint only after code runs.
- Do not chase stylistic perfection at the cost of physics progress.

Commands:

```text
python -m pytest code/tests -q
ruff check code
```

#### Report Auto-Builder

Purpose:

- Make the final report reproducible from the evidence bundle.

Implementation:

- Add `report/build_report.py`.
- It reads assumptions, validation metrics, summary CSVs, and figures.
- It generates a Markdown or LaTeX report draft.
- PDF generation is optional, depending on installed tools.

Output:

```text
report/LunaLink_Report_Draft.md
report/LunaLink_Report.pdf   optional if PDF toolchain exists
```

#### Scenario Export

Purpose:

- Make the tool feel interoperable with professional mission-analysis workflows.

Implementation:

- Add a simple export function that writes:
  - mission epoch
  - orbit elements
  - force model choice
  - ground station
  - simulation duration
  - subsystem baseline assumptions

Outputs:

```text
outputs/baseline/scenario/lunalink_scenario.json
outputs/baseline/scenario/lunalink_gmat_like.script
outputs/baseline/scenario/lunalink_orekit_like.json
```

These exports are documentation/interoperability aids. They do not need to be fully executable in GMAT or Orekit for the first version.

### 15.12 Coding-Harness Execution Rule

Adopt a fast evidence-action-validation loop:

1. Start from the most concrete file or failing check.
2. Gather only enough nearby context to make one local hypothesis.
3. Make the smallest grounded edit that advances the build.
4. Validate immediately with the narrowest useful test.
5. Broaden only after the narrow validation passes.

This mirrors modern coding-agent prompt-tuning evidence: less wandering, earlier grounded edits, and validation soon after edits.

### 15.13 NASA / ECSS Tailored Engineering Pack

Add a lightweight `qualification/` folder. This does not make the simulator flight-qualified or ECSS-certified. It makes the project look and behave like a carefully tailored professional engineering tool.

```text
qualification/
  tailoring_matrix.md
  requirements_baseline.md
  verification_control_document.md
  assumptions_register.csv
  interface_control_document.md
  model_limitations.md
  configuration_index.json
  risk_register.csv
  nonconformance_log.csv
  model_validation_report.md
  independent_review_checklist.md
  release_readiness_checklist.md
```

#### Tailoring Matrix

Create `qualification/tailoring_matrix.md`.

It should map NASA/ECSS themes to project actions:

```text
standard_or_guideline
theme
applicability: applied / tailored / not_applicable
project_action
evidence_artifact
justification
```

Example entries:

```text
NASA NPR 7150.2D | requirements traceability | applied | requirements_traceability.csv | outputs/baseline/requirements_traceability.csv
NASA-STD-8739.8B | software assurance and IV&V evidence | tailored | validation metrics and independent review checklist | qualification/
ECSS-E-ST-10 | systems engineering | tailored | mission assumptions, interfaces, margins, configuration index | qualification/
ECSS-E-ST-10-02 | verification | applied in lightweight form | verification control document | qualification/verification_control_document.md
ECSS-Q-ST-80 | software product assurance | tailored | tests, static checks, defect log, release checklist | qualification/
```

This is the key future-certification artifact: it shows what was followed, what was tailored, and what remains outside the project scope.

#### Verification Control Document

Create `qualification/verification_control_document.md`.

Each requirement must state:

```text
requirement_id
verification_method: test / analysis / inspection / demonstration
success_criterion
tolerance
evidence_artifact
status
```

Examples:

```text
REQ-ORB-001: analysis + test, period and duration verified from orbit output
REQ-EPS-001: analysis + test, SOC and sizing verified from energy balance
REQ-TTC-001: analysis + test, link margin verified from dB budget
REQ-GUI-001: demonstration, GUI launches and updates plots
REQ-RUN-001: demonstration, clean install and run command succeeds
```

#### Assumptions Register

Create `qualification/assumptions_register.csv`.

Each assumption records:

```text
assumption_id
subsystem
value
unit
source
justification
uncertainty_range
affected_outputs
```

This should include solar efficiency, degradation, battery DoD, coating alpha/epsilon, antenna gains, pointing losses, atmosphere density multiplier, residual magnetic dipole, and component thermal limits.

#### Interface Control Document

Create `qualification/interface_control_document.md`.

Each exchanged variable records:

```text
producer
consumer
variable
unit
frame
sign_convention
shape
valid_range
```

Priority interfaces:

- Orbit/environment to all subsystems.
- ADCS attitude and face normals to EPS/TCS/TT&C.
- EPS power and dissipation to TCS.
- TCS temperature flags to EPS/TT&C.
- TT&C pointing requests and transmitter loads to ADCS/EPS.

#### Configuration Index

Create `qualification/configuration_index.json`.

Record:

```text
python_version
package_versions
git_commit_if_available
scenario_id
epoch
orbit_interpretation
simulation_duration
random_seed
output_hashes_if_available
```

#### Model Limitations

Create `qualification/model_limitations.md`.

State clearly:

- Medium-fidelity preliminary design simulator.
- Not flight-qualified.
- Not ECSS-certified.
- No high-order gravity field beyond J2 baseline.
- No finite-element thermal model.
- No hardware-in-the-loop.
- No official ground-station hardware data unless later provided.
- No certified atmosphere, radiation, or spacecraft hardware database.

This is a strength, not a weakness: professional tools state their validity envelope.

#### Risk Register

Create `qualification/risk_register.csv`.

Each risk records:

```text
risk_id
description
likelihood
consequence
mitigation
residual_risk
owner
status
```

Minimum risks:

- Orbit-period ambiguity from brief.
- ADCS model numerical complexity.
- Thermal lumped-model limits.
- Atmosphere-density uncertainty near perigee.
- Link-budget assumptions without real hardware datasheets.
- GUI polish vs physics completion.
- Dependency installation failure.

#### Nonconformance Log

Create `qualification/nonconformance_log.csv`.

Use it to record any known issue that remains at delivery:

```text
nc_id
description
affected_requirement
severity
disposition: fixed / accepted_with_rationale / deferred
rationale
evidence
```

This is a professional habit: do not hide imperfections; disposition them.

#### Release Readiness Checklist

Create `qualification/release_readiness_checklist.md`.

Minimum release gates:

```text
all unit tests pass
headless baseline run succeeds
GUI imports and launches
validation table has no critical failures
assumptions JSON generated
traceability matrix generated
formula register generated
evidence bundle complete
README run commands verified
known limitations documented
```

#### Certification Readiness Levels

Use these internal labels:

```text
CRL-0: exploratory script
CRL-1: reproducible academic simulator
CRL-2: NASA/ECSS-inspired preliminary design tool
CRL-3: certification-ready evidence package
CRL-4: independently reviewed and authority-accepted tool for a defined use
CRL-5: flight-qualified simulator
```

Target for this project:

```text
CRL-2 baseline
CRL-3 stretch if the qualification folder is fully populated
```

Do not claim CRL-4 or CRL-5 without external independent review and formal authority acceptance.

### 15.14 Acceptable Claim Language

Use this language in README and report:

```text
NASA/ECSS-inspired medium-fidelity LunaLink mission engineering simulator
for preliminary subsystem design, visualization, validation, and trade studies.
```

Avoid:

```text
flight-qualified
ECSS-certified
NASA-certified
operational mission product
```

Only claim flight qualification after formal independent verification and validation plus acceptance by a responsible mission authority.

## 16. Expected Score After Execution

If executed cleanly:

```text
Physical correctness: 9.6-10 / 10
Visualization quality: 9.5-10 / 10
Engineering judgment: 10 / 10
User friendliness: 9.5-10 / 10
Overall assignment score: 9.8-10 / 10
Stretch possibility: 10 / 10 if GUI, validation, evidence, and report are all polished
```

Flight-grade rating:

```text
Flight-grade certification: 3-4 / 10
NASA/ECSS-inspired architecture: 9.2 / 10
Preliminary industry design usefulness: 9.0-9.3 / 10
Academic engineering validity: 9.6-10 / 10
```

Reason:

Actual flight-grade software requires formal requirements baselines, configuration management, independent V&V, validated mission data, safety analysis, review boards, and operational qualification. This project can imitate the discipline, but it cannot honestly claim that status.

## 17. My Confidence Rating

Confidence in building a complete runnable tool:

```text
9.1 / 10
```

Confidence in physics validity for the assignment:

```text
9.3 / 10
```

Confidence in reaching a top-tier submission:

```text
9.6 / 10
```

Main risks:

- ADCS numerical complexity.
- Time pressure from doing all four subsystems.
- GUI polish after the physics is complete.
- Dependency installation on a clean machine.

Risk control:

- Medium-fidelity models.
- Validation-first build.
- Deterministic evidence bundle.
- No unnecessary optimizer zoo.
- No heavy runtime dependency on GMAT, Orekit, Basilisk, or SPICE kernels.

## 18. Final Recommendation

Proceed with build.

The best version of this project is not a huge imitation of GMAT or Orekit. It is a focused LunaLink engineering workbench that borrows the best professional patterns:

- GMAT-style mission resources and events
- Orekit-style frames and propagator separation
- SPICE-style geometry discipline
- Basilisk-style subsystem data flow
- NASA-style V&V evidence
- Python-first clean execution

That is the path to a credible 10/10 tool for this PDF.
