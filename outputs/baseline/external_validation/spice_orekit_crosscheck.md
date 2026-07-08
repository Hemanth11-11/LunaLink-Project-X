# Independent SPICE + Orekit cross-check

This is an **executed** independent validation of the LunaLink models against two
professional flight-dynamics references:

- **NASA/NAIF SPICE** (`spiceypy` + DE440 planetary ephemeris) — truth for the
  Sun and Moon directions that drive eclipse and Moon-relay geometry.
- **Orekit 13.1** (numerical propagator, 8×8 gravity field + luni-solar third
  body) — truth for orbit propagation and the frozen-apsides property.

These references are **not** runtime dependencies of LunaLink (Orekit needs a JVM;
DE440 kernels are ~32 MB). They were run offline; only the results below ship in
the repository. Reproduce with `code/external_validation/spice_orekit_crosscheck.py`.

Epoch 2026-07-06T00:00:00Z, baseline orbit (500 × 36,000 km, i = 63.4°, ω = 270°).

## Results

| Quantity | LunaLink | Reference | Delta | Verdict |
| --- | --- | --- | --- | --- |
| Orbit period | 38464.343 s | 38464.343 s (Orekit) | < 0.01 s | ✅ exact |
| Apogee altitude | 36,000 km | 36,000 km (Orekit Kepler) | 0 km | ✅ |
| Perigee altitude | 500 km | 500 km (Orekit Kepler) | 0 km | ✅ |
| Position, 36 h, J2-only vs 8×8+luni-solar | — | Orekit | max 37.7 km, RMS 10.0 km | ✅ ~0.15 % of orbit |
| Sun direction (analytic) | Montenbruck | DE440 | max 0.37° | ✅ eclipse-adequate |
| Moon direction (analytic) | Montenbruck | DE440 | max 1.80° | ⚠️ screening only |
| Moon distance | 384,400 km (fixed) | 387,583 km (DE440, epoch) | 0.8 % | ⚠️ fixed-range assumption |
| **Argp drift, i = 63.4°** | analytic (J2) ≈ 0.0005°/day | **Orekit 0.004°/day** | < 0.004°/day | ✅ **frozen** |
| **Argp drift, i = 45°** | analytic (J2) 0.286°/day | **Orekit 0.293°/day** | 2.5 % | ✅ matches Kozai |

## Interpretation

1. **Orbit propagation is sound.** A pure two-body + J2 model reproduces the
   Orekit 8×8 + luni-solar trajectory to within ~38 km over the full 36 h
   simulation window (~0.15 % of the 24,628 km semi-major axis). J2-only is
   therefore adequate for contact-window and eclipse analysis on this timescale;
   the third-body/J3 terms only matter for multi-day/lifetime evolution.

2. **The 63.4° inclination is justified by physics, independently.** The J2
   apsidal drift vanishes at the critical inclination by construction; Orekit's
   full 8×8 + luni-solar model shows only a small residual (0.004°/day, ≈ 66×
   smaller than at 45°) coming from third-body perturbations. At the
   non-critical 45° the analytic Kozai secular rate in `lunalink/orbit_analysis.py`
   (0.286°/day) agrees with Orekit (0.293°/day) to 2.5 %. This is the reason a
   Molniya orbit holds its apogee over the northern hemisphere without continuous
   apsidal station-keeping.

3. **Ephemeris limitations are quantified, not hidden.** The analytic Sun is
   good to 0.37° (fine for eclipse). The analytic Moon is good to 1.8° in
   direction with a fixed 384,400 km range (true range 356k–406k km); it is used
   only as a relay-geometry *screening* model, consistent with how it is labelled
   in the code and dashboard.

Raw numbers: `spice_orekit_results.json`.
