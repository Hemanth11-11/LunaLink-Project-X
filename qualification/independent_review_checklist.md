# Independent Review Checklist

This checklist is prepared for a reviewer who did not author the code.

## Review Inputs

- `ProjectX_LunaLink_Brief_v2.pdf`
- `README.md`
- `outputs/baseline/validation_metrics.csv`
- `report/LunaLink_Baseline_Report.md`
- `qualification/model_limitations.md`
- `qualification/formula_register.md`
- `qualification/reference_matrix.md`

## Technical Checks

- [x] Orbit period matches 500 x 36,000 km altitude interpretation.
- [x] Simulation covers at least 36 h.
- [x] Ground contacts respect the 5 deg elevation mask.
- [x] EPS has no unserved energy and satisfies the 1.2 kW EOL validation.
- [x] Thermal component limits are not violated in baseline.
- [x] ADCS detumble metric passes and quaternion norm is tracked.
- [x] TT&C X-band and UHF margins exceed 3 dB in available geometry.
- [x] Monte Carlo and Latin Hypercube samples are reproducible.
- [x] Pareto EPS trade plot is generated.
- [x] Report is generated from the evidence bundle.
- [x] Dashboard starts in headless Streamlit smoke test.

## Open Independent Items

- [ ] Execute GMAT/Orekit scenario and compare orbit/contact/eclipses.
- [ ] Review subsystem assumptions against real hardware datasheets.
- [ ] Approve numerical tolerances with a responsible engineering authority.
- [ ] Decide whether any limitations are unacceptable for the intended use.
