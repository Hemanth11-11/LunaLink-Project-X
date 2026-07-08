# LunaLink All-Subsystem Simulation Plan

Date: 2026-07-06
Workspace: /home/godspeed/Downloads/Project X
Source brief: ProjectX_LunaLink_Brief_v2.pdf

## 1. Mission Understanding

The assignment asks for a Python simulation, GUI, and max 10 page report. The original brief says to choose one subsystem, but this project will simulate all four:

- EPS: electrical power generation, storage, and loads.
- TCS: thermal control with external faces and internal nodes.
- ADCS: attitude dynamics, disturbance torques, detumbling, pointing, and actuator sizing.
- TT&C: Earth downlink, Moon UHF link, contact windows, and data volume.

Fixed mission inputs from the brief:

- Orbit: HEO, Molniya-type, 500 x 36,000 km altitude, inclination 63.4 deg.
- Period in brief: approximately 12 hours.
- Spacecraft mass: 500 kg.
- Power budget at EOL: 1.2 kW.
- Design lifetime: at least 5 years.
- Earth downlink: X-band, at least 100 Mbps.
- Moon uplink: UHF, 400-512 MHz.
- Envelope: approximately 2.0 x 1.5 x 1.0 m box.
- Ground station: Ottobrunn, Germany, 48.07 N, 11.65 E.
- Minimum elevation: 5 deg.
- Simulation duration: at least 3 full orbits and at least 36 hours if using the stated 12 hour period.

## 2. Critical Assumptions and Ambiguities

These must be stated in the report and visible in the GUI.

1. Orbit period inconsistency:
   - A two-body Earth orbit with 500 x 36,000 km altitude has:
     - semi-major axis: 24,628.137 km
     - eccentricity: 0.720720
     - period: 10.685 h
   - A true 12 hour orbit with 500 km perigee would need apogee altitude about 39,964 km.
   - Baseline decision: use the fixed altitudes from the brief as authoritative, compute and display the actual period, and simulate at least 36 hours. Add an optional "exact 12 h sensitivity" mode only if time permits.

2. Missing orbital orientation:
   - Use argument of perigee = 270 deg, the standard Molniya choice that places apogee in the northern hemisphere.
   - Use RAAN = 0 deg for the reference case, with a GUI control if simple.
   - Use epoch = 2026-07-06 00:00:00 UTC unless changed by the user.

3. Spacecraft geometry:
   - Treat the spacecraft as a 2.0 x 1.5 x 1.0 m rectangular bus with homogeneous baseline inertia.
   - Inertia can be scaled by a margin factor to represent deployed panels, antennas, and equipment distribution.

4. Pointing modes:
   - EPS and TCS use simplified face normals from the current attitude mode.
   - ADCS supports detumbling, sun-pointing, and Earth-pointing.
   - TT&C assumes Earth downlink pointing during ground contacts and Moon-link pointing during Moon relay windows.

5. Thermal limits:
   - Use representative component operating limits unless specific hardware is later chosen:
     - electronics: -20 C to +60 C operating
     - battery: 0 C to +45 C preferred charge range
     - survival: -40 C to +85 C

6. Link budgets:
   - Earth downlink is X-band near 8.4 GHz at 100 Mbps.
   - Moon link is UHF at a configurable default of 450 MHz.
   - Required link margin is at least 3 dB for both links.

7. "Failproof" interpretation:
   - No aerospace simulation is failproof. The professional target is verification-driven: every plot and sizing output must trace to an equation, an assumption, and a sanity check.

## 3. Recommended Tool Strategy

### Core runtime dependencies

These should be installable with pip and should run cleanly:

- numpy: vector math and arrays.
- scipy: ODE integration using solve_ivp.
- pandas: tabular time-series outputs.
- astropy: time, units, Sun/Moon approximate ephemerides, coordinate support.
- matplotlib: headless plots for main_simulation.py.
- plotly: interactive GUI plots.
- streamlit: fast Python GUI with sliders, tabs, plots, and tables.
- pytest: verification tests.

### Optional validation references, not core dependencies

Use these to cross-check design choices and cite in the report, but avoid making the student submission depend on them:

- NASA GMAT: independent orbit/contact sanity checks.
- Orekit: professional flight dynamics reference for frames, propagation, eclipse, and visibility.
- NASA NAIF SPICE / SpiceyPy: high-quality Sun/Moon/geometry reference if kernels are available.
- Basilisk: high-fidelity ADCS/GN&C comparison for future extension.
- NOAA/NCEI IGRF-14: reference geomagnetic model. Baseline implementation may use dipole or simplified IGRF to stay robust.
- pymsis: optional atmosphere density reference. For this HEO mission, drag is only important near perigee and can be a bounded-order-of-magnitude model in the first pass.

### Why not build around GMAT/Orekit/Basilisk directly?

The submission must be Python, runnable with pip, and likely judged under time pressure. GMAT is not a pip dependency, Orekit needs Java/Python wrapper setup, and Basilisk is powerful but heavy for a 10 page student deliverable. The right engineering choice is:

1. Build a transparent Python model.
2. Validate key outputs against trusted tools or hand calculations.
3. Cite limitations honestly.

## 4. Software Architecture

Proposed folder structure:

```text
code/
  main_simulation.py
  main_gui.py
  requirements.txt
  lunalink/
    constants.py
    config.py
    orbit.py
    environment.py
    geometry.py
    eps.py
    thermal.py
    adcs.py
    ttc.py
    plotting.py
    validation.py
  tests/
    test_orbit.py
    test_environment.py
    test_eps.py
    test_thermal.py
    test_adcs.py
    test_ttc.py
report/
  LunaLink_Report.pdf
README.txt
```

Data flow:

1. MissionConfig stores all fixed and user-adjustable assumptions.
2. orbit.py generates spacecraft position, velocity, ground track, eclipse state, slant range, and elevation.
3. environment.py computes Sun vector, Moon vector, Earth IR/albedo approximations, atmosphere density, and magnetic field.
4. Each subsystem consumes the same time grid and environment state.
5. Results are merged into one pandas DataFrame for plotting, tables, and GUI.

## 5. Orbit and Environment Plan

### Model

- Propagate an Earth-centered inertial state for at least 36 hours.
- Baseline force model:
  - central Earth gravity
  - J2 perturbation
  - optional simple drag near perigee
  - optional solar radiation pressure for ADCS disturbance torque only
- Use scipy solve_ivp with fixed output cadence.
- Recommended output cadence:
  - 60 s for final simulation
  - 120-300 s for fast GUI preview
- Convert ECI to Earth-fixed frame using a simplified GMST rotation or astropy if reliable.
- Compute ground station topocentric elevation from Ottobrunn.
- Compute eclipse with a Sun-vector Earth occultation test.
- Compute Moon direction using astropy built-in ephemerides to avoid large downloads.

### Verification

- Two-body period matches the computed 10.685 h within numerical tolerance.
- Specific orbital energy is nearly conserved in two-body mode.
- Perigee and apogee altitudes match 500 km and 36,000 km within tolerance.
- Elevation contact windows start/end near 5 deg threshold.
- Eclipse intervals are physically plausible and correlate with Earth shadow geometry.

## 6. EPS Plan

### Engineering model

Inputs:

- Solar constant at 1 AU: about 1361 W/m^2.
- Solar-cell EOL efficiency: configurable, default 28-30 percent after 5 year degradation.
- Solar array packing factor, pointing loss, temperature loss, and power conditioning efficiency.
- Power modes:
  - safe
  - nominal
  - peak relay, capped by 1.2 kW EOL budget
- Payload/relay duty cycle.
- Battery chemistry: Li-ion baseline.
- Depth of discharge limit: default 30-40 percent for life margin.

Equations:

- Generated power:
  - P_gen = solar_flux * array_area * eta_EOL * cos(theta) * pointing_factor * bus_efficiency * eclipse_flag
- Battery energy:
  - dE/dt = P_gen - P_load
- Required battery capacity:
  - C_batt >= max_eclipse_energy_deficit / allowed_DoD * margin
- Required array area:
  - A_array sized so orbit-average generated energy covers load energy plus recharge margin.

Outputs:

- Power generation vs consumption over time.
- Battery state of charge.
- Solar array area in m^2.
- Battery capacity in Wh.
- Power budget table per mode.

Verification:

- Battery state of charge never exceeds physical bounds.
- Eclipse causes discharge; sunlight causes recharge.
- Increasing duty cycle reduces minimum state of charge.
- Array area and battery capacity are in credible order of magnitude for a 500 kg, 1.2 kW spacecraft.

## 7. TCS Plan

### Engineering model

Use a lumped-parameter model with:

- Six external face nodes.
- One internal equipment node.
- Optional battery node if time permits.

Heat balance:

- Q_solar + Q_albedo + Q_EarthIR + Q_internal = Q_stored + Q_rad_out + Q_conduction

External heat inputs:

- Direct solar flux when not eclipsed.
- Earth albedo with a configurable albedo coefficient.
- Earth IR with a configurable effective flux.
- Deep-space sink temperature near 3 K for radiation.

Surface properties:

- white paint
- black paint
- aluminized/FEP radiator-like coating
- MLI-like insulated face approximation

Equations:

- C_i dT_i/dt = sum(Q_in) - epsilon_i sigma A_i (T_i^4 - T_space^4) + conduction terms
- Internal node receives dissipated electrical power from the active power mode.

Outputs:

- External surface temperatures for all six faces.
- Internal equipment temperature.
- Hot/cold case equilibrium estimates.
- Flags for operating/survival temperature violations.

Verification:

- Isolated radiator equilibrium temperature matches hand-calculated blackbody estimates.
- White coating runs cooler than black coating under sun exposure.
- Internal power increase raises internal node temperature.
- Eclipse causes cooling trend unless internal dissipation dominates.

## 8. ADCS Plan

### Engineering model

Baseline spacecraft inertia:

- Ixx = 1/12 m (y^2 + z^2)
- Iyy = 1/12 m (x^2 + z^2)
- Izz = 1/12 m (x^2 + y^2)

Attitude state:

- Quaternion q_BI.
- Body angular velocity omega_B.
- Reaction wheel momentum vector h_rw.

Disturbance torques:

- Gravity gradient:
  - tau_gg = 3 mu / r^3 * r_hat x (I r_hat)
- Solar radiation pressure:
  - area, reflectivity coefficient, center-of-pressure offset.
- Aerodynamic drag near perigee:
  - simple density model and center-of-pressure offset.
- Residual magnetic dipole torque:
  - tau_m = m_residual x B.

Actuators:

- Magnetorquers:
  - torque = m_cmd x B
  - dipole saturation, default sized from required detumble time and local B-field range.
- Reaction wheels:
  - torque capacity
  - momentum capacity
  - maximum rpm
  - desaturation using magnetorquers when threshold is exceeded.

Control modes:

- Detumbling:
  - B-dot controller, m_cmd = -k * dB/dt, saturated.
- Sun-pointing:
  - quaternion/attitude-error PD control using reaction wheels.
- Earth-pointing:
  - target local nadir or ground station direction during downlink.

Outputs:

- Angular velocity over time.
- Detumbling convergence.
- Reaction wheel momentum and desaturation triggers.
- Disturbance torque magnitude vs orbit position.
- Sun-pointing or Earth-pointing error.
- Animated 3D attitude view in GUI if time permits.

Verification:

- Quaternion norm remains near 1.
- Detumbling reduces angular velocity from initial 10 deg/s.
- Magnetorquer torque is always perpendicular to B.
- Wheel momentum grows under disturbance torque and drops during desaturation.
- Controller saturation is visible and not hidden.

## 9. TT&C Plan

### Geometry model

Earth ground contact:

- Ground station at Ottobrunn.
- Contact when elevation >= 5 deg.
- Compute slant range, elevation, azimuth, duration, and data volume.

Moon link:

- Use Moon vector from astropy built-in ephemeris.
- Compute spacecraft-Moon slant range.
- Check Earth occultation of the line from spacecraft to Moon.
- Apply pointing constraint if antenna is directional.

### Link budget model

Use dB accounting:

- EIRP = P_tx_dBW + G_tx_dBi - L_tx_dB
- FSPL = 20 log10(4 pi R / lambda)
- C/N0 = EIRP + G/T - FSPL - losses + 228.6
- Eb/N0 = C/N0 - 10 log10(data_rate)
- margin = Eb/N0 - required_EbN0

Include:

- pointing loss
- polarization loss
- atmospheric/rain loss for X-band
- implementation loss
- receiver noise temperature
- antenna gains

Outputs:

- Link budget table for Earth downlink and Moon UHF link.
- Slant range and elevation time series.
- Contact window start/end/duration.
- Data volume per contact and total data return.
- Ground track with visibility/contact overlays.

Verification:

- FSPL increases with range and frequency.
- Contact windows only occur above 5 deg.
- Earth downlink margin is at least 3 dB for accepted design points.
- Data volume equals data rate times contact duration times efficiency.

## 10. GUI Plan

Use Streamlit with Plotly.

First screen:

- Global mission controls in a sidebar.
- Orbit summary cards: period, perigee, apogee, eclipse time, number of contacts.
- Tabs for EPS, TCS, ADCS, TT&C, and Assumptions.

Interactive controls:

- EPS: payload duty cycle, power mode, solar efficiency, array area, battery capacity.
- TCS: coating selection, internal dissipation, face orientation/pointing mode.
- ADCS: initial tumble rate, magnetorquer dipole, wheel capacity, pointing mode.
- TT&C: antenna gains, transmitter power, data rate, losses, min elevation.

GUI quality rules:

- Plot axes have units.
- Warnings appear when physics constraints are violated.
- No hidden magic numbers: assumptions are shown in a table.
- Live update uses cached orbit/environment so sliders stay responsive.

## 11. Report Plan, Max 10 Pages

Because all four subsystems are included, the report must be compact.

Recommended page allocation:

1. Mission context, scope, and the orbit-period ambiguity.
2. Assumptions table and chosen toolchain.
3. Orbit/environment model and validation checks.
4. EPS equations, sizing, and key plots.
5. TCS equations, coating trade, and key plots.
6. ADCS sizing, detumbling/pointing, and key plots.
7. TT&C contact windows, link budget, and data volume.
8. Integrated trade discussion: power, thermal, pointing, and communication coupling.
9. How AI was used and what was independently checked.
10. References.

## 12. Implementation Order

The deadline in the brief is 2026-07-08 23:59. Starting from 2026-07-06, this is an aggressive two-day build. The plan prioritizes correctness and runnable deliverables before polish.

Phase 1: shared physics backbone

- Implement config, constants, orbit propagation, eclipse, ground station visibility.
- Verify: unit tests plus generated orbit/contact plots.

Phase 2: TT&C and EPS

- Implement link budget, contact windows, data volume.
- Implement solar array and battery model.
- Verify: link margin table, SOC plot, energy balance tests.

Phase 3: TCS

- Implement six-face lumped thermal model and coating table.
- Verify: blackbody sanity tests and hot/cold case outputs.

Phase 4: ADCS

- Implement inertia, disturbance torques, B-dot detumbling, simple reaction-wheel pointing.
- Verify: quaternion norm, angular velocity convergence, wheel momentum limits.

Phase 5: GUI and report

- Streamlit tabs and Plotly figures.
- Headless main_simulation.py generates all plots without GUI.
- README.txt explains pip install and run commands.
- Report cites assumptions, equations, results, and AI usage.

## 13. Success Criteria

The project is successful when all of the following are true:

- `pip install -r requirements.txt` works on a clean Python environment.
- `python main_simulation.py` runs headless and produces all required plots/tables.
- `streamlit run main_gui.py` launches the GUI.
- The simulation covers at least 36 hours.
- All four subsystems produce the required outputs from the brief.
- Every engineering assumption is visible in code/config/report.
- EPS has no unexplained energy creation or negative battery state.
- TCS temperatures respond correctly to coating, eclipse, and dissipation changes.
- ADCS quaternion remains normalized and detumbling converges.
- TT&C link budgets show at least 3 dB margin for accepted links.
- README is short and sufficient for first-time execution.
- Report stays within 10 pages and includes references.

## 14. Key Risks and Mitigations

Risk: all four subsystems exceed the original one-subsystem scope.
Mitigation: build a transparent medium-fidelity model for each subsystem instead of one very high-fidelity model that does not run.

Risk: orbit period conflict could be penalized.
Mitigation: explicitly state the computed period and simulate at least 36 hours. Include optional exact-12-hour sensitivity if time allows.

Risk: ADCS becomes too complex.
Mitigation: keep B-dot detumbling and PD pointing simple, visible, and testable. Show limitations clearly.

Risk: thermal model false precision.
Mitigation: present TCS as lumped-parameter engineering approximation, with hot/cold cases and coating trends rather than claiming detailed finite-element accuracy.

Risk: GUI performance.
Mitigation: cache orbit/environment results and use coarse time step for live preview.

Risk: external data downloads break clean install.
Mitigation: use astropy built-in ephemerides and optional validators only.

## 15. Reference Sources Checked

Primary/official and high-credibility sources used to ground this plan:

- NASA Small Spacecraft Technology State-of-the-Art, 2026: https://www.nasa.gov/smallsat-institute/sst-soa/
- NASA SoA Power chapter: https://www.nasa.gov/smallsat-institute/sst-soa/power-subsystems/
- NASA SoA Guidance, Navigation, and Control chapter: https://www.nasa.gov/smallsat-institute/sst-soa/guidance-navigation-and-control/
- NASA SoA Thermal Control chapter: https://www.nasa.gov/smallsat-institute/sst-soa/thermal-control/
- NASA SoA Communications chapter: https://www.nasa.gov/smallsat-institute/sst-soa/soa-communications/
- NASA/NAIF SPICE: https://naif.jpl.nasa.gov/naif/
- GMAT official wiki: https://gmat.atlassian.net/wiki/spaces/GW/overview
- GMAT SourceForge project: https://sourceforge.net/projects/gmat/
- Orekit official site and documentation: https://www.orekit.org/
- Basilisk official documentation: https://hanspeterschaub.info/basilisk/
- Basilisk GitHub repository: https://github.com/AVSLab/basilisk
- NOAA/NCEI IGRF: https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field
- Astropy solar-system ephemerides documentation: https://docs.astropy.org/en/stable/coordinates/solarsystem.html
- SciPy solve_ivp documentation: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
- SpiceyPy documentation and JOSS citation: https://spiceypy.readthedocs.io/en/main/
- pymsis repository: https://github.com/SWxTREC/pymsis

Useful research papers to cite where relevant:

- Annex et al. (2020), "SpiceyPy: a Pythonic Wrapper for the SPICE Toolkit", Journal of Open Source Software.
- Biscani and Izzo (2020), "A parallel global multiobjective framework for optimization: pagmo", Journal of Open Source Software.
- Picone et al. (2002), "NRLMSISE-00 empirical model of the atmosphere: Statistical comparisons and scientific issues", Journal of Geophysical Research.
- Alken et al. (2021), "International Geomagnetic Reference Field: the thirteenth generation", Earth, Planets and Space. Use NOAA/NCEI page for IGRF-14 update details.
- Gaite (2010), "Nonlinear analysis of spacecraft thermal models", arXiv.
- Willis et al. (2024), "Building a Better B-Dot: Fast Detumbling with Non-Monotonic Lyapunov Functions", arXiv.

