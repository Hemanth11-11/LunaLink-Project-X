# Model Limitations

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
