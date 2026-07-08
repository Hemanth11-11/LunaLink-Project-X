# LunaLink Engineering Simulation Report

## Scope

This report summarizes the Python evidence bundle for the LunaLink project brief: the fixed 500 x 36,000 km, 63.4 deg orbit and all four selected subsystems: EPS, TCS, ADCS, and TT&C.

The simulator is engineering-preliminary and NASA/ECSS-inspired. It is not flight-qualified, certified, or accepted for operations without formal IV&V, independent tool correlation, and authority approval.

## Run Manifest

- Mode: `quick`
- J2 enabled: `True`
- Critical validation failures: `False`
- Figure count: `7`

## Validation Metrics

| name | status | value | criterion | source_module |
| --- | --- | --- | --- | --- |
| fixed_altitude_orbit_period_h | pass | 10.684539794233128 | Expected about 10.6845 h for 500 x 36,000 km orbit | orbit |
| simulation_duration_h | pass | 36.0 | Must be at least 36 h | environment |
| minimum_altitude_km | pass | 500.0000000000009 | Should remain near the 500 km perigee altitude | orbit |
| maximum_altitude_km | pass | 36229.20190267842 | Should remain near the 36,000 km apogee altitude with J2 tolerance | orbit |
| minimum_contact_elevation_rad | pass | 0.08846763733282152 | All contacts must be above configured minimum elevation | environment |
| eclipse_samples | pass | 7 | Eclipse count is scenario-dependent; value is recorded for evidence | environment |
| eps_minimum_state_of_charge | pass | 0.7672067901234568 | Preliminary EPS reserve should stay at or above 20% SOC | eps |
| eps_unserved_energy_j | pass | 0.0 | No unserved load energy in the baseline run | eps |
| eps_array_eol_power_w | pass | 1927.0126800000003 | Solar array EOL power should meet or exceed the 1.2 kW brief value | eps |
| eps_peak_load_w | pass | 1200.0 | Peak modeled load should not exceed the 1.2 kW EOL power budget | eps |
| eps_average_load_w | pass | 1100.9259259259259 | Average modeled load should stay below the 1.2 kW EOL power budget | eps |
| thermal_component_limit_flag | pass | False | No thermal component limit flags in the baseline run | thermal |
| adcs_final_angular_speed_deg_s | pass | 0.03559388768946665 | Detumble demonstration should end below 0.05 deg/s | adcs |
| adcs_wheel_saturated | pass | False | Reaction wheel storage should not saturate in the baseline run | adcs |
| ttc_xband_min_margin_db | pass | 5.12768736134484 | X-band link margin should exceed the 3 dB threshold | ttc |
| ttc_uhf_min_margin_db | pass | 5.493496500738104 | UHF link margin should exceed the 3 dB threshold | ttc |
| ttc_xband_data_rate_bps | pass | 100000000.0 | Earth downlink should meet at least 100 Mbps when available | ttc |

## Subsystem Summary

### EPS

- sample_count: `217`
- duration_s: `129600`
- array_area_m2: `6`
- eta_eol: `0.27`
- array_pointing_mode: `sun_tracking`
- array_eol_power_w: `1927.01`
- battery_capacity_kwh: `4.5`
- battery_capacity_j: `1.62e+07`
- initial_soc: `0.8`
- final_soc: `1`
- min_soc: `0.767207`
- max_soc: `1`
- max_depth_of_discharge: `0.232793`
- battery_energy_swing_kwh: `1.04757`
- total_generated_energy_j: `2.42225e+08`
- total_load_energy_j: `1.4268e+08`
- net_energy_j: `9.95455e+07`
- average_generation_w: `1869.02`
- average_load_w: `1100.93`
- peak_generated_power_w: `1927.01`
- peak_load_w: `1200`
- minimum_array_incidence_factor: `0`
- average_array_incidence_factor: `0.969907`
- min_power_margin_w: `-1200`
- eclipse_duration_s: `4200`
- sunlight_duration_s: `125400`
- ground_contact_duration_s: `94200`
- peak_load_duration_s: `100200`
- curtailed_energy_j: `9.02199e+07`
- unserved_energy_j: `0`

### THERMAL

- coating: `mixed`
- face_coatings: `{'x_pos': 'white', 'x_neg': 'MLI', 'y_pos': 'white', 'y_neg': 'MLI', 'z_pos': 'MLI', 'z_neg': 'OSR/FEP'}`
- power_w: `1101.38`
- average_power_w: `1101.38`
- peak_power_w: `1200`
- duration_s: `129600`
- min_temp_k: `253.753`
- max_temp_k: `341.629`
- final_internal_temp_k: `314.361`
- min_internal_temp_k: `293.009`
- max_internal_temp_k: `322.628`
- component_limit_flags: `{'internal_cold': False, 'internal_hot': False, 'external_cold': False, 'external_hot': False}`
- component_limit_flag: `False`

### ADCS

- initial_angular_speed_deg_s: `10`
- final_angular_speed_deg_s: `0.0355939`
- max_commanded_dipole_a_m2: `400`
- max_wheel_momentum_nms: `0.162685`
- wheel_saturated: `False`
- desaturation_events: `0`
- wheel_momentum_capacity_nms: `12`
- magnetorquer_max_dipole_a_m2: `400`
- max_total_torque_nm: `0.00516434`
- max_disturbance_torque_nm: `0.000132173`
- max_q_norm_error: `2.22045e-16`
- wheel_model_scope: `preliminary disturbance momentum bookkeeping, not closed-loop sizing`

### TTC

- xband_contact_windows: `[{'start_s': 1800.0, 'end_s': 37200.0, 'duration_s': 35400.0}, {'start_s': 49800.0, 'end_s': 67800.0, 'duration_s': 18000.0}, {'start_s': 79200.0, 'end_s': 114600.0, 'duration_s': 35400.0}, {'start_s': 124200.0, 'end_s': 129600.0, 'duration_s': 5400.0}]`
- xband_available_windows: `[{'start_s': 1800.0, 'end_s': 37200.0, 'duration_s': 35400.0}, {'start_s': 49800.0, 'end_s': 67800.0, 'duration_s': 18000.0}, {'start_s': 79200.0, 'end_s': 114600.0, 'duration_s': 35400.0}, {'start_s': 124200.0, 'end_s': 129600.0, 'duration_s': 5400.0}]`
- xband_contact_duration_s: `94200`
- xband_available_duration_s: `94200`
- xband_data_volume_bits: `9.42e+12`
- xband_min_margin_db: `5.12769`
- xband_max_margin_db: `17.9258`
- xband_data_rate_bps: `1e+08`
- uhf_visibility_windows: `[{'start_s': 0.0, 'end_s': 36000.0, 'duration_s': 36000.0}, {'start_s': 39000.0, 'end_s': 75000.0, 'duration_s': 36000.0}, {'start_s': 77400.0, 'end_s': 114000.0, 'duration_s': 36600.0}, {'start_s': 116400.0, 'end_s': 129600.0, 'duration_s': 13200.0}]`
- uhf_available_windows: `[{'start_s': 0.0, 'end_s': 36000.0, 'duration_s': 36000.0}, {'start_s': 39000.0, 'end_s': 75000.0, 'duration_s': 36000.0}, {'start_s': 77400.0, 'end_s': 114000.0, 'duration_s': 36600.0}, {'start_s': 116400.0, 'end_s': 129600.0, 'duration_s': 13200.0}]`
- uhf_visibility_duration_s: `121800`
- uhf_available_duration_s: `121800`
- uhf_data_volume_bits: `1.218e+09`
- uhf_min_margin_db: `5.4935`
- uhf_max_margin_db: `6.35545`
- uhf_data_rate_bps: `10000`
- aggregate_independent_link_volume_bits: `9.42122e+12`
- end_to_end_relay_volume_bits: `1.218e+09`
- total_data_volume_bits: `9.42122e+12`
- data_volume_note: `Total is aggregate independent link volume; end-to-end relay is min(UHF, X-band).`
- uhf_geometry_model: `Moon-center range with Earth occultation screening only.`

## EPS Design Trade

The Pareto-style table ranks array/battery combinations by unserved energy and minimum state of charge.

| array_area_m2 | battery_capacity_kwh | min_soc | final_soc | unserved_energy_j | curtailed_energy_j |
| --- | --- | --- | --- | --- | --- |
| 5 | 6 | 0.775405 | 1 | 0 | 5.11884e+07 |
| 6 | 6 | 0.775405 | 1 | 0 | 8.91399e+07 |
| 7 | 6 | 0.775405 | 1 | 0 | 1.27089e+08 |
| 4 | 6 | 0.775183 | 1 | 0 | 1.32271e+07 |
| 5 | 4.5 | 0.767207 | 1 | 0 | 5.22684e+07 |

## Evidence Files

- Mission and subsystem time histories are stored as CSV files.
- Scenario exports are stored under `scenario_exports/`.
- Figures are stored under `figures/`.

## Core References

- NASA/SP-2016-6105 Rev 2, NASA Systems Engineering Handbook.
- NASA-STD-8739.8B, Software Assurance and Software Safety Standard.
- ECSS-E-ST-10C, Space Engineering - System engineering general requirements.
- ECSS-Q-ST-80C, Space Product Assurance - Software product assurance.
- Vallado, Fundamentals of Astrodynamics and Applications.
- Wertz, Space Mission Analysis and Design.
- Gilmore, Spacecraft Thermal Control Handbook.
- CCSDS Radio Frequency and Modulation Systems recommendations.
