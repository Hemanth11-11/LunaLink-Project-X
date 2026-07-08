# LunaLink Engineering-Grade Integrated Architecture

Date: 2026-07-07
Purpose: consolidated specialist-agent review and final design direction for a high-credibility all-subsystem LunaLink simulation.

This document supplements `LunaLink_AllSubsystems_Professional_Plan.md`. It is the result of a multi-role review across:

- Orbit and environment
- EPS
- Thermal control
- ADCS/GNC
- TT&C/RF communications
- Software architecture, verification, and report evidence

The goal is not to claim flight qualification. The goal is a 10/10 academic engineering tool: physically honest, traceable, reproducible, and difficult for a reviewer to dismiss.

## 1. Definition of "10/10" for This Project

A perfect score tool should do five things exceptionally well:

1. Use one shared physical truth source for orbit, time, frames, Sun/Moon geometry, eclipse, ground contact, magnetic field, and environmental fluxes.
2. Make every subsystem consume that same truth source instead of creating private geometry or private assumptions.
3. Use models that are medium-fidelity but defensible: clear equations, explicit assumptions, unit consistency, and known limitations.
4. Produce an evidence bundle where every report plot, sizing number, margin, and warning is reproducible from a headless run.
5. Show validation metrics, not just attractive plots.

This is the engineering-grade compromise: transparent and correct enough to defend, still simple enough to run cleanly with pip.

## 2. Specialist Council Decisions

### Decision 1: Orbit Truth

Use the fixed altitudes from the brief:

- Perigee altitude: 500 km
- Apogee altitude: 36,000 km
- Inclination: 63.4 deg

Do not silently force a 12 hour period. The two-body period is:

```text
r_p = 6878.137 km
r_a = 42378.137 km
a = 24628.137 km
e = 0.720720
T = 38464 s = 10.6845 h
```

Therefore:

```text
36 h simulation = 3.37 actual fixed-altitude orbits
```

A true 12 h orbit with 500 km perigee would need apogee altitude about 39,964 km. That can be included as a labeled sensitivity case, not the baseline.

### Decision 2: Shared Environment Table

Every subsystem consumes the same time-indexed table:

```text
time_utc
r_eci_m, v_eci_mps
r_ecef_m, lat_rad, lon_rad, alt_m
true_anomaly_rad
sun_hat_eci, moon_hat_eci
eclipse_flag, solar_flux_w_m2
gs_range_m, gs_elevation_rad, gs_azimuth_rad, gs_contact_flag
moon_range_m, moon_occulted_flag
earth_view_factor_per_face
earth_ir_flux_w_m2
albedo_flux_w_m2
magnetic_field_eci_t
atmospheric_density_kg_m3
face_normals_eci
```

This table is the spine of the whole project.

### Decision 3: Core Dependencies

Use:

- numpy
- scipy
- pandas
- matplotlib
- plotly
- streamlit
- astropy, but only with built-in ephemerides unless a validator mode is enabled
- pytest

Do not make GMAT, Orekit, Basilisk, SPICE kernels, or pymsis hard runtime dependencies. They are professional validation references, not submission blockers.

### Decision 4: Internal Units

Use SI internally:

- meters
- seconds
- kilograms
- watts
- kelvin
- tesla
- radians

Only convert for display. This is non-negotiable because mixed km/m errors can corrupt orbit, link budgets, torque, and thermal outputs.

### Decision 5: GUI Is a View, Not a Physics Engine

`main_simulation.py` is authoritative. `main_gui.py` calls the same simulation core. No subsystem physics should live only in Streamlit callbacks.

## 3. Baseline Design Numbers

These are the first-order numbers that should appear in the assumptions table and report.

### Orbit

```text
semi-major axis: 24628.137 km
eccentricity: 0.720720
period: 10.6845 h
orbits in 36 h: 3.37
perigee speed: about 9.99 km/s
apogee speed: about 1.62 km/s
```

At critical inclination, argument-of-perigee drift should be near zero under J2. RAAN drift should be small over 36 h, roughly -0.17 deg/day order of magnitude.

### Spacecraft Inertia

For a homogeneous `2.0 x 1.5 x 1.0 m`, `500 kg` box:

```text
Ixx = 135.4 kg m^2
Iyy = 208.3 kg m^2
Izz = 260.4 kg m^2
```

Use a design inertia margin of 1.25 to 1.30:

```text
I_design ~= diag(176, 271, 339) kg m^2
```

### EPS

Recommended baseline:

```text
solar array: deployable triple-junction GaAs
area: 6.0 m^2
eta_BOL: 0.30
5 year degradation factor: 0.90
eta_EOL: about 0.27
EOL bus power density: 270-300 W/m^2
battery: Li-ion
battery capacity: 4.0-4.5 kWh baseline
nominal DoD limit: 35 percent
emergency DoD limit: 40 percent
```

Load modes:

```text
safe: 250-350 W
nominal: 750-950 W
peak relay/downlink: 1100-1200 W
```

Treat 1.2 kW as a hard EOL bus-load ceiling. The GUI should warn above 1.08 kW for margin and flag hard violations above 1.2 kW.

### Thermal

Use 7 nodes:

- Six external face nodes
- One internal equipment node

Face areas:

```text
+/-X: 1.5 m^2 each
+/-Y: 2.0 m^2 each
+/-Z: 3.0 m^2 each
total external area: 13.0 m^2
```

Recommended coatings:

```text
white paint: alpha 0.18-0.25, epsilon 0.80-0.90
black paint: alpha 0.90-0.98, epsilon 0.85-0.95
OSR/FEP radiator: alpha 0.08-0.15, epsilon 0.75-0.85
MLI effective surface: alpha 0.10-0.20, epsilon 0.03-0.08
```

Key rule: do not let all faces radiate efficiently. That makes the spacecraft unrealistically easy to cool. Use MLI-like non-radiator faces plus explicit radiator faces.

### ADCS

Initial tumble:

```text
10 deg/s = 0.1745 rad/s
H0 worst-axis baseline ~= 45.5 Nms
H0 with inertia margin ~= 59 Nms
```

Magnetic field issue:

```text
rough B near perigee: about 25 microtesla
rough B near apogee: about 0.1 microtesla
```

Do not treat magnetorquers like constant-authority LEO actuators. In this HEO, magnetic control is useful mainly near perigee.

Recommended actuators:

```text
magnetorquers: +/-300 A m^2 baseline, +/-400-500 A m^2 preferred
reaction wheel torque: 0.05 Nm minimum, 0.10 Nm preferred
reaction wheel momentum: 8-12 Nms minimum, 15-20 Nms preferred
desat threshold: 60-70 percent of wheel capacity
```

### TT&C

Earth X-band downlink baseline:

```text
frequency: 8.4 GHz
data rate: 100 Mbps
spacecraft RF power: 20 W
spacecraft HGA: 0.6 m parabolic, eta 0.60, gain about 32.2 dBi
ground dish: 3.0 m, eta 0.62, gain about 46.4 dBi
ground Tsys: 150 K
atmosphere/rain: 1.5 dB
polarization: 0.5 dB
pointing losses: 1.2 dB total
implementation loss: 2.0 dB
required Eb/N0: 5.0 dB coded assumption
required final margin: at least 3 dB
```

Worst fixed-orbit Earth downlink design range:

```text
about 42,000 km
FSPL at 8.4 GHz and 42,000 km: about 203.4 dB
baseline margin: about 3-4 dB
```

Healthier reserve case:

```text
0.7 m spacecraft HGA + 3.7 m ground dish -> about 8 dB margin
```

Moon UHF link baseline:

```text
frequency: 450 MHz, GUI range 400-512 MHz
data rate: 10 kbps default
lunar Tx power: 25 W
lunar Tx antenna: 20 dBi directional
spacecraft Rx antenna: 18 dBi directional
spacecraft receiver Tsys: 500 K
required Eb/N0: 6.0 dB
```

Moon UHF at 450 MHz:

```text
range envelope: about 315,000-450,000 km
FSPL: about 195.5-198.6 dB
10 kbps directional link margin: about 4-7 dB
```

Do not model Moon UHF as a high-rate service. Default should be 1-10 kbps depending on antenna assumptions.

## 4. Software Architecture

Use this refined layout:

```text
code/
  main_simulation.py
  main_gui.py
  requirements.txt
  lunalink/
    constants.py
    config.py
    orbit.py
    frames.py
    environment.py
    geometry.py
    eps.py
    thermal.py
    adcs.py
    ttc.py
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
report/
README.txt
```

Module ownership:

- `constants.py`: SI constants only.
- `config.py`: dataclasses, defaults, assumption validation, scenario presets.
- `orbit.py`: propagation, orbital elements, eclipse primitive.
- `frames.py`: ECI/ECEF/topocentric transforms.
- `environment.py`: Sun, Moon, Earth IR, albedo, B-field, density.
- `eps.py`: solar generation, loads, battery, sizing.
- `thermal.py`: lumped thermal nodes, coatings, component flags.
- `adcs.py`: attitude dynamics, disturbances, controllers, actuators.
- `ttc.py`: contacts, link budgets, data volume.
- `simulation.py`: orchestrator, run schedule, result merging.
- `validation.py`: pass/fail metrics with tolerances.
- `plotting.py`: figure builders only.
- `io.py`: output manifest, CSV, JSON, file writing.

No plotting or Streamlit imports inside physics modules.

## 5. Orbit and Environment Implementation

Baseline propagation:

```text
a_total = -mu r/r^3 + a_J2
```

J2 acceleration:

```text
a_J2 = 1.5 J2 mu Re^2 / r^5 *
       [x(5z^2/r^2 - 1),
        y(5z^2/r^2 - 1),
        z(5z^2/r^2 - 3)]
```

Eclipse:

```text
in_shadow = dot(r_sc, s_hat) < 0
            and norm(r_sc - dot(r_sc, s_hat) s_hat) < Re
```

Ground contact:

```text
rho = r_sc_ecef - r_gs_ecef
elevation = atan2(rho_up, sqrt(rho_east^2 + rho_north^2))
contact = elevation >= 5 deg
```

Moon occultation:

```text
r_los = r_moon - r_sc
s_star = clamp(-dot(r_sc, r_los) / norm(r_los)^2, 0, 1)
d_min = norm(r_sc + s_star r_los)
blocked = d_min < Re + clearance
```

Validation:

- Period = 10.6845 h for the fixed-altitude baseline.
- Perigee/apogee match 500 km and 36,000 km.
- Two-body energy and angular momentum are conserved in two-body test mode.
- J2 run shows near-zero argument-of-perigee drift at 63.4 deg.
- Contact windows never include elevation below 5 deg.
- Eclipse flag changes EPS and TCS behavior.

## 6. EPS Implementation

Power generation:

```text
P_sa(t) = S0 A_sa eta_EOL f_pack f_temp eta_pcdu
          max(0, n_sa dot s_hat) I_sun(t)
```

Load:

```text
P_load(t) = P_bus_mode
          + P_payload duty_payload(t)
          + P_ttc contact_flag(t)
          + P_adcs(mode)
          + P_heater(T)
```

Battery:

```text
P_net = P_sa - P_load
dE_batt/dt = eta_ch max(P_net, 0) + min(P_net, 0) / eta_dis
SOC = E_batt / C_batt_EOL
```

Sizing:

```text
A_sa >= M_sa E_required_sun / (P_density_EOL T_sun)
C_batt_BOL >= M_batt E_deficit_max / (DoD_allow eta_dis f_capacity_EOL)
```

Integration:

- Receives Sun vector, eclipse, array pointing cosine from ADCS.
- Receives TT&C contact modes and transmitter load.
- Receives TCS battery/array temperature for derating and charge inhibit.
- Outputs available power, SOC, low-power flags, heater power demand, and mode feasibility.

## 7. Thermal Implementation

For each external face:

```text
C_i dT_i/dt =
  alpha_i A_i q_solar_i
+ alpha_i A_i q_albedo_i
+ epsilon_i sigma A_i [F_E,i T_E^4 + (1 - F_E,i) T_space^4 - T_i^4]
+ G_i (T_int - T_i)
+ sum_j G_ij (T_j - T_i)
```

Internal node:

```text
C_int dT_int/dt =
  Q_diss(mode, duty, t)
+ Q_battery_loss
+ Q_heater
- sum_i G_i (T_int - T_i)
```

Earth view factor first-order approximation:

```text
F_E,i = (Re / r)^2 max(0, n_i dot (-r_hat))
```

At perigee this can be about 0.86 for a nadir-facing surface; at apogee about 0.023.

Use `solve_ivp` with `max_step = 30-60 s` for final runs. GUI preview can use 120 s only after convergence is demonstrated.

Integration:

- Receives EPS dissipation and heater command.
- Receives ADCS face normals and pointing mode.
- Outputs internal/equipment temperatures, battery charge inhibit, array thermal derate, component limit flags.

## 8. ADCS Implementation

Rigid-body dynamics:

```text
I omegadot = tau_ext + tau_rw - omega x (I omega + h_rw)
hdot_rw = -tau_rw
```

Quaternion or DCM propagation must use one declared convention and tests.

Disturbance torques:

```text
tau_gg = 3 mu / r^3 * rhat_B x (I rhat_B)
tau_srp = sum(r_CoP_i x F_srp_i)
tau_drag = r_CoP x (-0.5 rho Cd A v_rel^2 vhat_rel)
tau_mag_res = m_res x B
```

B-dot:

```text
m_cmd = -k_Bdot dB_B/dt
clip to m_max
tau_mtq = m_cmd x B
```

Reaction-wheel pointing gains:

```text
Kp_i = I_i omega_n^2
Kd_i = 2 zeta I_i omega_n
```

Recommended:

```text
zeta = 0.8-1.0
omega_n = 0.007-0.015 rad/s
```

Desaturation:

```text
h_perp = h_rw - (h_rw dot Bhat) Bhat
tau_des = -k_h h_perp
m_des = (B x tau_des) / |B|^2
```

Enable routine desaturation mainly when `|B| > 5 microtesla`.

Mode sequence:

```text
DETUMBLE -> SAFE_SUN -> SUN_POINT -> EARTH_POINT / MOON_POINT -> DESAT windows
```

Integration:

- Receives TT&C pointing requests.
- Receives EPS actuator power constraints.
- Receives thermal constraints if pointing exposes radiator or battery face.
- Outputs attitude, face normals, pointing errors, wheel momentum, desat flags, torque components, actuator power.

## 9. TT&C Implementation

Antenna gain:

```text
G_dBi = 10 log10(eta (pi D / lambda)^2)
```

Free-space path loss:

```text
FSPL = 92.45 + 20 log10(R_km) + 20 log10(f_GHz)
```

Carrier-to-noise density:

```text
EIRP = 10 log10(P_tx_W) + G_tx - L_tx
G/T = G_rx - 10 log10(T_sys)
C/N0 = EIRP + G/T - FSPL - losses + 228.6
Eb/N0 = C/N0 - 10 log10(R_bps) - L_impl
margin = Eb/N0 - Eb/N0_required
```

Availability:

```text
available = geometry_ok
            and margin >= 3 dB
            and ADCS_pointing_ok
            and EPS_power_ok
            and thermal_ok
```

Data volume:

```text
V_bits = integral(R_bps(t) eta_contact available(t) dt)
```

Integration:

- Receives Earth contact geometry, Moon range, and occultation.
- Receives ADCS antenna pointing error.
- Receives EPS power availability.
- Receives TCS thermal flags.
- Outputs contact windows, margins, data volume, transmitter load schedule.

## 10. Cross-Subsystem Couplings

These are the interactions that make the tool feel engineering-grade rather than four disconnected demos.

### EPS -> TCS

Electrical load becomes internal heat:

```text
Q_diss ~= heat_fraction * P_load
```

Battery inefficiency becomes heat during charge/discharge.

### TCS -> EPS

Solar array efficiency derates with panel temperature:

```text
eta_array(T) = eta_ref [1 + gamma (T_panel - 298 K)]
gamma ~= -0.003 to -0.004 / K
```

Battery charging is inhibited or heater load is added below 0 C.

### ADCS -> EPS/TCS/TT&C

Attitude sets:

- Solar-array incidence
- Face heating
- Radiator exposure
- Antenna pointing
- Earth/Moon link losses

### TT&C -> EPS/TCS/ADCS

Downlink creates:

- Peak power load
- Internal heat
- Earth-pointing demand
- Possible solar pointing compromise

### Orbit -> Everyone

Orbit phase sets:

- Eclipse
- Earth IR/albedo
- magnetic control authority
- drag disturbance near perigee
- contact windows
- slant range and link margin

## 11. Validation Matrix

Use automated validation metrics. Each metric should have:

```text
name
value
tolerance
status: pass/warn/fail
severity
source_module
```

Required checks:

| Area | Checks |
|---|---|
| Orbit | Period, perigee/apogee, 36 h duration, two-body energy, J2 critical inclination behavior |
| Frames | ECI/ECEF consistency, station elevation threshold, longitude wrap |
| Environment | Eclipse geometry, Sun/Moon vector unit norms, Earth view factor bounds |
| EPS | SOC bounds, eclipse discharge, sunlight recharge, energy balance residual, baseline sizing range |
| TCS | Kelvin positivity, face area sum, coating ordering, heat-balance residual, component limit flags |
| ADCS | Quaternion norm, torque-free conservation, B-dot convergence, torque perpendicular to B, desat behavior |
| TT&C | FSPL slope, antenna gain formula, X-band margin, UHF margin, data-volume integration |
| Integration | Downlink raises EPS load and TCS heat, ADCS pointing loss affects link margin, thermal flags affect EPS/TT&C |

## 12. Evidence Bundle

The final headless run should write:

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
  figures/
    orbit_groundtrack.png
    eclipse_contact_timeline.png
    eps_power_soc.png
    thermal_faces_internal.png
    adcs_detumble_pointing.png
    adcs_torques_wheel_momentum.png
    ttc_range_margin_data.png
```

The report must use only this evidence bundle for final numbers.

## 13. Build Priority

Given the deadline pressure, build in this order:

1. `config`, `constants`, `orbit`, `frames`, `environment`
2. `validation` skeleton and baseline evidence output
3. EPS
4. TT&C
5. TCS
6. ADCS simplified but physically honest
7. Streamlit GUI
8. Report

Reason: EPS and TT&C can be highly credible once orbit/environment works. TCS is moderately coupled. ADCS has the most numerical risk and should remain bounded.

## 14. "Do Not Fool Yourself" Rules

- Do not hide the orbit-period inconsistency.
- Do not use separate time grids per subsystem unless interpolation is explicit.
- Do not let the GUI own any physics.
- Do not mix km and m.
- Do not make all thermal faces high-emissivity radiators.
- Do not assume magnetorquers work equally well at apogee.
- Do not make Moon UHF high-rate by accident.
- Do not force reaction wheel desaturation by choosing unrealistic tiny wheels.
- Do not claim precision for drag density unless using a proper atmosphere model.
- Do not report a margin without showing assumptions.

## 15. Final Professional Position

The most defensible LunaLink tool is not a giant high-fidelity simulator. It is a transparent, validated, medium-fidelity mission engineering workbench.

The architecture should make it obvious that:

- The orbit and environment drive everything.
- Power, thermal, attitude, and communications are coupled.
- Assumptions are exposed.
- Warnings are generated from physics and margins.
- The same code path produces GUI plots and report evidence.

That is what makes the project look like serious aerospace engineering rather than a collection of disconnected Python plots.

## 16. Source Anchors

Useful official or high-credibility anchors:

- NASA Small Spacecraft Technology State-of-the-Art, 2026: https://www.nasa.gov/smallsat-institute/sst-soa/
- NASA Systems Engineering Handbook: https://www.nasa.gov/reference/systems-engineering-handbook/
- NASA Software Engineering Handbook: https://swehb.nasa.gov/
- NASA/NAIF SPICE: https://naif.jpl.nasa.gov/naif/
- GMAT: https://gmat.atlassian.net/wiki/spaces/GW/overview
- Orekit: https://www.orekit.org/
- Basilisk: https://hanspeterschaub.info/basilisk/
- NOAA/NCEI IGRF: https://www.ncei.noaa.gov/products/international-geomagnetic-reference-field
- Astropy solar-system ephemerides: https://docs.astropy.org/en/stable/coordinates/solarsystem.html
- SciPy solve_ivp: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html

