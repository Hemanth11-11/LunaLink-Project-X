# Expanded Reference Review

## Directly Useful For LunaLink

- NASA Small Spacecraft Technology State of the Art, Power Subsystems:
  representative spacecraft power-generation, storage, distribution, and
  degradation context for the EPS model.
- NASA Small Spacecraft Technology State of the Art, Thermal Control:
  passive/active thermal-control technologies and spacecraft thermal-balance
  framing for the TCS model.
- NASA Small Spacecraft Technology State of the Art, Guidance, Navigation and
  Control: small-spacecraft attitude actuators, sensors, and GNC architecture
  context for the ADCS scope.
- NASA Small Spacecraft Technology State of the Art, Communications:
  communications subsystem context for X-band downlink and UHF relay assumptions.
- Vallado, Fundamentals of Astrodynamics and Applications:
  Keplerian element definitions, J2 perturbation, ECI/ECEF rotations, and
  ground-station geometry.
- Montenbruck and Gill, Satellite Orbits:
  higher-fidelity force-model, frame, and orbit-determination upgrade path.
- Wertz, Space Mission Analysis and Design:
  spacecraft-subsystem sizing and early mission-trade context.
- Gilmore, Spacecraft Thermal Control Handbook:
  radiation balance, coating properties, thermal margins, and thermal-network
  model interpretation.
- Wertz, Spacecraft Attitude Determination and Control; Markley and Crassidis;
  Sidi: quaternion kinematics, Euler rigid-body dynamics, and magnetic/torque
  control context.
- CCSDS and JPL DESCANSO references:
  RF link-budget structure, C/N0, Eb/N0, link margin, coding/modulation and
  deep-space communications practices.

## Tool And Process References

- NASA-STD-7009B, Standard for Models and Simulations:
  credibility evidence, uncertainty, verification, validation, and model
  acceptance expectations.
- NASA/SP-2016-6105 Rev 2, NASA Systems Engineering Handbook:
  requirements, assumptions, verification, interfaces, and risk structure.
- NASA-STD-8739.8B and NASA NPR 7150.2:
  software assurance and software engineering life-cycle expectations.
- ECSS-E-ST-10C, ECSS-E-ST-40C, and ECSS-Q-ST-80C:
  European system-engineering, software-engineering, and software-product
  assurance tailoring.
- GMAT and Orekit:
  independent astrodynamics correlation references for orbit/contact/eclipse
  validation.
- Basilisk/Vizard:
  benchmark architecture for high-fidelity GN&C simulation, Monte Carlo, and
  3D spacecraft visualization.

## Useful But Out Of Current Scope

- Trajectory-optimization literature such as differential evolution, NSGA-II,
  MBH, SLSQP, and low-thrust methods is useful for transfer design or
  station-keeping optimization. It is not required by the Project X brief
  because the orbit is fixed.
- Hardware-in-the-loop, processor-in-the-loop, and real-time simulator
  references are useful for future industry qualification, but they exceed the
  current Python-only student submission scope.
