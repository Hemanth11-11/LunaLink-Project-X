# LunaLink Engineering Simulation Report

## Scope

This report summarizes the Python evidence bundle for the LunaLink project brief: the fixed 500 x 36,000 km, 63.4 deg orbit and all four selected subsystems: EPS, TCS, ADCS, and TT&C.

The simulator is engineering-preliminary and NASA/ECSS-inspired. It is not flight-qualified, certified, or accepted for operations without formal IV&V, independent tool correlation, and authority approval.

## Run Manifest

- Mode: `baseline`
- J2 enabled: `True`
- Critical validation failures: `False`
- Figure count: `7`

## Validation Metrics

| name | status | value | criterion | source_module |
| --- | --- | --- | --- | --- |
| fixed_altitude_orbit_period_h | pass | 10.684539794233128 | Expected about 10.6845 h for 500 x 36,000 km orbit | orbit |
| simulation_duration_h | pass | 36.0 | Must be at least 36 h | environment |
| minimum_altitude_km | pass | 500.0000000000009 | Should remain near the 500 km perigee altitude | orbit |
| maximum_altitude_km | pass | 36229.9574504823 | Should remain near the 36,000 km apogee altitude with J2 tolerance | orbit |
| orbit_critical_inclination_deg | pass | 63.4 | Inclination should sit at the 63.43 deg critical value | orbit_analysis |
| orbit_frozen_apsides_argp_rate_deg_per_day | pass | 0.0004654701051559739 | Apsidal drift must be near zero (Orekit-verified 0.004 deg/day at 63.4 deg) | orbit_analysis |
| minimum_contact_elevation_rad | pass | 0.08762296873739589 | All contacts must be above configured minimum elevation | environment |
| eclipse_samples | pass | 70 | Eclipse count is scenario-dependent; value is recorded for evidence | environment |
| eps_minimum_state_of_charge | pass | 0.7538966049382716 | Preliminary EPS reserve should stay at or above 20% SOC | eps |
| eps_unserved_energy_j | pass | 0.0 | No unserved load energy in the baseline run | eps |
| eps_array_eol_power_w | pass | 1927.0126800000003 | Solar array EOL power should meet or exceed the 1.2 kW brief value | eps |
| eps_peak_load_w | pass | 1200.0 | Peak modeled load should not exceed the 1.2 kW EOL power budget | eps |
| eps_average_load_w | pass | 1098.3796296296296 | Average modeled load should stay below the 1.2 kW EOL power budget | eps |
| thermal_component_limit_flag | pass | False | No thermal component limit flags in the baseline run | thermal |
| thermal_worst_operating_margin_k | pass | 7.632638911303559 | Preliminary hot/cold thermal margin should be at least 5 K | thermal |
| adcs_final_angular_speed_deg_s | pass | 0.025901690354961412 | Detumble demonstration should end below 0.05 deg/s | adcs |
| adcs_wheel_saturated | pass | False | Preliminary disturbance momentum bookkeeping should not exceed assumed capacity | adcs |
| ttc_xband_min_margin_db | pass | 5.12739305815262 | X-band link margin should exceed the 3 dB threshold | ttc |
| ttc_uhf_min_margin_db | pass | 5.4934794046042725 | UHF link margin should exceed the 3 dB threshold | ttc |
| ttc_xband_data_rate_bps | pass | 100000000.0 | Earth downlink should meet at least 100 Mbps when available | ttc |
| adcs_sun_pointing_settled_error_deg | pass | 0.011217117519769608 | Closed-loop sun-pointing should settle below its 3 deg requirement | adcs |
| adcs_dipole_vs_igrf_max_rel_diff | pass | 0.3859594901502412 | Aligned dipole should track IGRF-14 magnitude within ~40% | adcs |
| ttc_xband_atmos_loss_5deg_db | pass | 2.5741244290145273 | ITU-R X-band rain+gas loss at 5 deg should be a credible 1-6 dB | comms |
| ttc_ccsds_coding_gain_db | pass | 8.0 | CCSDS coding should provide several dB of gain over uncoded BPSK | comms |
| radiation_annual_dose_krad | pass | 15.254112003494381 | Belt dose should be a credible 5-60 krad(Si)/yr for this HEO | radiation |
| radiation_array_remaining_power_5yr | pass | 0.9486442431951079 | Derived 5-yr array power fraction should stay above 0.80 | radiation |

## Subsystem Summary

### EPS

- sample_count: `2161`
- duration_s: `129600`
- array_area_m2: `6`
- eta_eol: `0.27`
- array_pointing_mode: `sun_tracking`
- array_eol_power_w: `1927.01`
- battery_capacity_kwh: `4.5`
- battery_capacity_j: `1.62e+07`
- initial_soc: `0.8`
- final_soc: `1`
- min_soc: `0.753897`
- max_soc: `1`
- max_depth_of_discharge: `0.246103`
- battery_energy_swing_kwh: `1.10747`
- total_generated_energy_j: `2.41705e+08`
- total_load_energy_j: `1.4235e+08`
- net_energy_j: `9.93552e+07`
- average_generation_w: `1865.01`
- average_load_w: `1098.38`
- peak_generated_power_w: `1927.01`
- peak_load_w: `1200`
- minimum_array_incidence_factor: `0`
- average_array_incidence_factor: `0.967824`
- min_power_margin_w: `-1200`
- eclipse_duration_s: `4200`
- sunlight_duration_s: `125400`
- ground_contact_duration_s: `94020`
- peak_load_duration_s: `99420`
- curtailed_energy_j: `8.99163e+07`
- unserved_energy_j: `0`

### THERMAL

- coating: `mixed`
- face_coatings: `{'x_pos': 'white', 'x_neg': 'MLI', 'y_pos': 'white', 'y_neg': 'MLI', 'z_pos': 'MLI', 'z_neg': 'OSR/FEP'}`
- attitude_assumption: `LVLH/nadir-pointing bus; not ADCS quaternion coupled`
- power_w: `1098.43`
- average_power_w: `1098.43`
- peak_power_w: `1200`
- duration_s: `129600`
- min_temp_k: `258.342`
- max_temp_k: `331.938`
- final_internal_temp_k: `307.316`
- min_internal_temp_k: `293.15`
- max_internal_temp_k: `315.517`
- min_external_temp_k: `258.342`
- max_external_temp_k: `331.938`
- internal_cold_margin_k: `30`
- internal_hot_margin_k: `7.63264`
- external_cold_margin_k: `85.1925`
- external_hot_margin_k: `41.2122`
- worst_cold_margin_k: `30`
- worst_hot_margin_k: `7.63264`
- worst_operating_margin_k: `7.63264`
- component_limit_flags: `{'internal_cold': False, 'internal_hot': False, 'external_cold': False, 'external_hot': False}`
- component_limit_flag: `False`

### ADCS

- initial_angular_speed_deg_s: `10`
- final_angular_speed_deg_s: `0.0259017`
- max_commanded_dipole_a_m2: `400`
- max_wheel_momentum_nms: `0.149616`
- wheel_saturated: `False`
- desaturation_events: `0`
- wheel_momentum_capacity_nms: `12`
- magnetorquer_max_dipole_a_m2: `400`
- max_total_torque_nm: `0.00516434`
- max_disturbance_torque_nm: `0.00018616`
- max_q_norm_error: `2.22045e-16`
- control_mode_scope: `B-dot detumble and disturbance torque bookkeeping`
- pointing_validation_scope: `not included in the baseline model`
- wheel_model_scope: `preliminary disturbance momentum bookkeeping, not closed-loop sizing`

### ADCS_POINTING

- initial_pointing_error_deg: `67.2976`
- final_pointing_error_deg: `0.000743654`
- settled_mean_pointing_error_deg: `0.00134635`
- settled_max_pointing_error_deg: `0.0112171`
- pointing_requirement_met: `True`
- max_wheel_momentum_nms: `1.11609`
- max_q_norm_error: `2.22045e-16`
- settle_error_deg: `3`

### TTC

- xband_contact_windows: `[{'start_s': 1620.0, 'end_s': 37200.0, 'duration_s': 35580.0}, {'start_s': 49380.0, 'end_s': 67260.0, 'duration_s': 17880.0}, {'start_s': 79080.0, 'end_s': 114240.0, 'duration_s': 35160.0}, {'start_s': 124200.0, 'end_s': 129600.0, 'duration_s': 5400.0}]`
- xband_refined_contact_windows: `[{'start_s': 1582.0358983334227, 'end_s': 37183.328808878665, 'duration_s': 35601.29291054524}, {'start_s': 49370.72840343094, 'end_s': 67230.2083484097, 'duration_s': 17859.479944978753}, {'start_s': 79039.82098725412, 'end_s': 114226.77740424513, 'duration_s': 35186.956416991015}, {'start_s': 124174.07043261241, 'end_s': 129600.0, 'duration_s': 5425.9295673875895}]`
- xband_available_windows: `[{'start_s': 1620.0, 'end_s': 37200.0, 'duration_s': 35580.0}, {'start_s': 49380.0, 'end_s': 67260.0, 'duration_s': 17880.0}, {'start_s': 79080.0, 'end_s': 114240.0, 'duration_s': 35160.0}, {'start_s': 124200.0, 'end_s': 129600.0, 'duration_s': 5400.0}]`
- xband_contact_duration_s: `94020`
- xband_available_duration_s: `94020`
- xband_data_volume_bits: `9.402e+12`
- xband_min_margin_db: `5.12739`
- xband_max_margin_db: `18.1718`
- xband_data_rate_bps: `1e+08`
- uhf_visibility_windows: `[{'start_s': 0.0, 'end_s': 36000.0, 'duration_s': 36000.0}, {'start_s': 38460.0, 'end_s': 74940.0, 'duration_s': 36480.0}, {'start_s': 77280.0, 'end_s': 113880.0, 'duration_s': 36600.0}, {'start_s': 116100.0, 'end_s': 129600.0, 'duration_s': 13500.0}]`
- uhf_available_windows: `[{'start_s': 0.0, 'end_s': 36000.0, 'duration_s': 36000.0}, {'start_s': 38460.0, 'end_s': 74940.0, 'duration_s': 36480.0}, {'start_s': 77280.0, 'end_s': 113880.0, 'duration_s': 36600.0}, {'start_s': 116100.0, 'end_s': 129600.0, 'duration_s': 13500.0}]`
- uhf_visibility_duration_s: `122580`
- uhf_available_duration_s: `122580`
- uhf_data_volume_bits: `1.2258e+09`
- uhf_min_margin_db: `5.49348`
- uhf_max_margin_db: `6.35545`
- uhf_data_rate_bps: `10000`
- aggregate_independent_link_volume_bits: `9.40323e+12`
- end_to_end_relay_volume_bits: `1.2258e+09`
- total_data_volume_bits: `9.40323e+12`
- data_volume_note: `Total is aggregate independent link volume; end-to-end relay is min(UHF, X-band).`
- xband_window_model: `Sampled flags plus linearly interpolated 5 deg elevation crossings.`
- uhf_geometry_model: `Moon-center range with Earth occultation screening only.`

### ORBIT

- critical_inclination_deg: `63.4349`
- inclination_deg: `63.4`
- analytic_argp_rate_deg_per_day: `0.00046547`
- analytic_raan_rate_deg_per_day: `-0.170765`
- station_keeping_delta_v_m_s_per_year: `3.63515`
- station_keeping_delta_v_5yr_m_s: `18.1758`
- inclination_drift_deg_per_year: `0.128507`

### RADIATION

- peak_l_shell: `33.3445`
- fraction_in_belts: `0.22721`
- annual_fluence_1mev_e_cm2: `1.06779e+13`
- fluence_5yr_1mev_e_cm2: `5.33894e+13`
- array_remaining_power_5yr: `0.948644`
- annual_dose_krad_si_estimate: `15.2541`
- note: `Parametric AE-8-class belt model; engineering estimate, not AE9/AP9.`

### MAGNETIC

- igrf_available: `True`
- n_samples: `109`
- mean_igrf_dipole_ratio: `0.949742`
- max_relative_difference: `0.385959`

### COMMS

- itur_available: `True`
- atmos_loss_5deg_db: `2.57412`
- atmos_loss_zenith_db: `0.210038`
- atmos_loss_contact_mean_db: `0.517026`
- atmos_loss_contact_max_db: `2.56871`
- ccsds_scheme: `rs_conv_concatenated`
- ccsds_required_ebn0_db: `2.5`
- ccsds_coding_gain_db: `8`
- max_doppler_khz: `84.9039`
- exceedance_pct: `1`

## EPS Design Trade

The Pareto-style table ranks array/battery combinations by unserved energy and minimum state of charge.

| array_area_m2 | battery_capacity_kwh | min_soc | final_soc | unserved_energy_j | curtailed_energy_j |
| --- | --- | --- | --- | --- | --- |
| 5 | 6 | 0.765422 | 1 | 0 | 5.09691e+07 |
| 6 | 6 | 0.765422 | 1 | 0 | 8.88363e+07 |
| 7 | 6 | 0.765422 | 1 | 0 | 1.26703e+08 |
| 4 | 6 | 0.7654 | 1 | 0 | 1.31017e+07 |
| 5 | 4.5 | 0.753897 | 1 | 0 | 5.20491e+07 |

## Formula And Requirement Traceability

| requirement_id | formula_id | reference | implementation_path | test_path | validation_metric | evidence_artifact |
| --- | --- | --- | --- | --- | --- | --- |
| REQ-MIS-001 | F-ORB-001,F-ORB-002,F-ORB-003,F-ORB-004 | Vallado; NASA Systems Engineering Handbook | code/lunalink/orbit.py; code/lunalink/config.py | code/tests/test_orbit.py; code/tests/test_simulation.py | fixed_altitude_orbit_period_h; minimum_altitude_km; maximum_altitude_km | validation_metrics.csv; mission_timeseries.csv |
| REQ-MIS-003 | F-GEO-001,F-FRAME-001 | Vallado; WGS84 geodetic station geometry | code/lunalink/frames.py; code/lunalink/environment.py | code/tests/test_frames.py; code/tests/test_ttc.py | minimum_contact_elevation_rad | mission_timeseries.csv; ttc_timeseries.csv |
| REQ-EPS-001 | F-EPS-001,F-EPS-002 | NASA SmallSat SOA Power; Wertz SMAD | code/lunalink/eps.py | code/tests/test_eps.py | eps_minimum_state_of_charge; eps_unserved_energy_j; eps_array_eol_power_w | eps_timeseries.csv; validation_metrics.csv |
| REQ-TCS-001,REQ-TCS-002 | F-TCS-001,F-TCS-002 | Gilmore Spacecraft Thermal Control Handbook; NASA SmallSat SOA Thermal | code/lunalink/thermal.py | code/tests/test_thermal.py | thermal_component_limit_flag; thermal_worst_operating_margin_k | thermal_timeseries.csv; validation_metrics.csv |
| REQ-ADCS-001 | F-ADCS-001,F-ADCS-002,F-ADCS-003 | Wertz SMAD; NASA SmallSat SOA GNC | code/lunalink/adcs.py | code/tests/test_adcs.py | adcs_final_angular_speed_deg_s; adcs_wheel_saturated | adcs_timeseries.csv; validation_metrics.csv |
| REQ-TTC-001,REQ-TTC-002 | F-TTC-001,F-TTC-002,F-TTC-003 | CCSDS RF recommendations; JPL DESCANSO | code/lunalink/ttc.py | code/tests/test_ttc.py | ttc_xband_min_margin_db; ttc_uhf_min_margin_db; ttc_xband_data_rate_bps | ttc_timeseries.csv; validation_metrics.csv |
| REQ-TRADE-001 | F-TRADE-001 | Design of experiments; Latin Hypercube sampling literature | code/lunalink/trades.py | code/tests/test_trades.py | reproducible fixed-seed samples | lhs_samples.csv; monte_carlo_samples.csv |
| REQ-XCHK-001 | F-ORB-001,F-GEO-001 | GMAT/Orekit independent astrodynamics correlation workflow | code/lunalink/exporters.py | code/tests/test_main_simulation.py | external correlation pending; scenario export complete | scenario_exports/LunaLink_external_validation_recipe.md |

## Artifact Hashes

| artifact | sha256 |
| --- | --- |
| run_manifest.json | 92d61dd9a7864b7d9204b4e31dc28e33de707fb9e8b5e4b3b1e901b28dde919d |
| validation_metrics.csv | c4708b238cacee92e1949fa097c88107e0c105ff6ae725607f1372d356437e54 |
| subsystem_summaries.json | 206900ec7b49d40aec3e7bb0d358a29bd6951941ea214f2912648023202951ac |
| formula_traceability.csv | d66940cc8a303d9cdaed1c7125eb69e8ba94cf9ce0754c7f84272a6c06ad4c1f |
| mission_timeseries.csv | 1c3badd99082c7ba59f513a3972f8db81714e524603768398f544d1f161ec874 |
| eps_timeseries.csv | f93cf53313e81840f1c1baa86d67647787146eb03570c5123fcb65dd35c66e87 |
| thermal_timeseries.csv | 7a939e1cf06b9369b13a6e78cb02ce9d51c2d2f837a14e85211bf1efc8229e45 |
| adcs_timeseries.csv | d94ac1ddc9cdf9a3b417d650305d3edf5853fc9d475b2dc6ff905fa10723d2d5 |
| ttc_timeseries.csv | 0173218a7e025c986c2f88dd5e903519da981ebe7ef1e2de2b4b030c9314b552 |

## Figures

- orbit_groundtrack.png: `/home/hemanth/Downloads/Project X/outputs/baseline/figures/orbit_groundtrack.png`
- eclipse_contact_timeline.png: `/home/hemanth/Downloads/Project X/outputs/baseline/figures/eclipse_contact_timeline.png`
- eps_power_soc.png: `/home/hemanth/Downloads/Project X/outputs/baseline/figures/eps_power_soc.png`
- thermal_faces_internal.png: `/home/hemanth/Downloads/Project X/outputs/baseline/figures/thermal_faces_internal.png`
- adcs_detumble_pointing.png: `/home/hemanth/Downloads/Project X/outputs/baseline/figures/adcs_detumble_pointing.png`
- ttc_range_margin_data.png: `/home/hemanth/Downloads/Project X/outputs/baseline/figures/ttc_range_margin_data.png`
- pareto_eps_trade.png: `/home/hemanth/Downloads/Project X/outputs/baseline/figures/pareto_eps_trade.png`

## Open Nonconformance Log

| nc_id | description | affected_requirement | severity | disposition | rationale | evidence |
| --- | --- | --- | --- | --- | --- | --- |
| NC-001 | Formal GMAT/Orekit numerical comparison has not been executed. | REQ-XCHK-001 | major | deferred | Scenario exports exist; independent tool execution requires external setup and review. | outputs/baseline/scenario_exports/ |
| NC-002 | Moon UHF geometry uses Moon-center range and Earth occultation screening, not a lunar surface relay asset. | REQ-TTC-001 | major | accepted_with_rationale | Adequate for preliminary RF sizing; limitations documented. | qualification/model_limitations.md |
| NC-003 | Thermal model is lumped-parameter, not finite-element thermal analysis. | REQ-TCS-001 | major | accepted_with_rationale | Assignment-level preliminary thermal trends and limits are covered. | qualification/model_limitations.md |
| NC-004 | ADCS wheel momentum is preliminary bookkeeping, not closed-loop wheel sizing. | REQ-ADCS-001 | major | accepted_with_rationale | Full Euler dynamics and disturbance torques are modeled; hardware sizing remains future work. | qualification/model_limitations.md |
| NC-005 | No independent IV&V or authority acceptance has been performed. | ALL | critical | deferred | Cannot be completed by the development agent; requires independent organization/authority. | qualification/release_readiness_checklist.md |

## Model Limitations

## Current Claim Boundary

The current simulator is suitable for early mission/subsystem design reasoning,
requirements discussion, and repeatable evidence generation. It is not a
flight-dynamics operations tool, not a thermal vacuum qualification model, and
not a certified software product.

## Known Simplifications

- Orbit propagation uses central gravity with optional J2, not full high-order
  geopotential, third-body gravity, SRP, maneuvers, or station-keeping.
- Sun and Moon geometry are approximate analytic engineering models.
- Eclipse uses a cylindrical shadow approximation.
- Atmosphere, Sun, Moon, and magnetic field are simplified engineering trend
  models.
- ADCS includes full Euler rate dynamics and basic disturbance torques, but its
  wheel momentum output is preliminary bookkeeping, not closed-loop wheel sizing
  or hardware-in-the-loop validation. The baseline validates detumble behavior,
  not closed-loop pointing accuracy.
- Thermal is a lumped low-order mixed-coating face model, not a detailed
  finite-element thermal network. Face heating assumes a nominal LVLH/nadir
  bus orientation and is not coupled to the ADCS quaternion history.
- TT&C uses deterministic link budgets with simple availability flags; it does
  not model weather statistics, antenna pattern errors, acquisition, coding
  implementation, lunar surface relay geometry, regulatory coordination, or
  interference.
- EPS uses aggregate array and load assumptions; it includes array incidence
  modes but does not model full harness, converter, degradation, or cell-level
  battery behavior.

## Upgrade Path

The next realism upgrades are GMAT/Orekit cross-correlation, higher-fidelity
ephemerides, validated thermal optical properties, detailed antenna pointing,
and explicit uncertainty propagation through subsystem margins.

## Evidence Files

- Mission and subsystem time histories are stored as CSV files.
- Scenario exports are stored under `scenario_exports/`.
- Figures are stored under `figures/`.
- Formula traceability is stored in `formula_traceability.csv`.

## Core References

- NASA/SP-2016-6105 Rev 2, NASA Systems Engineering Handbook.
- NASA-STD-8739.8B, Software Assurance and Software Safety Standard.
- ECSS-E-ST-10C, Space Engineering - System engineering general requirements.
- ECSS-Q-ST-80C, Space Product Assurance - Software product assurance.
- Vallado, Fundamentals of Astrodynamics and Applications.
- Wertz, Space Mission Analysis and Design.
- Gilmore, Spacecraft Thermal Control Handbook.
- CCSDS Radio Frequency and Modulation Systems recommendations.
