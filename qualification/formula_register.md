# Formula Register

This register records the main equations implemented in the preliminary tool.

| ID | Area | Formula | Implementation |
| --- | --- | --- | --- |
| F-ORB-001 | Orbit period | `T = 2*pi*sqrt(a^3/mu)` | `OrbitConfig.period_s` |
| F-ORB-002 | Eccentricity | `e = (r_a - r_p)/(r_a + r_p)` | `OrbitConfig.eccentricity` |
| F-ORB-003 | Two-body acceleration | `a = -mu*r/|r|^3` | `lunalink.orbit` |
| F-ORB-004 | J2 perturbation | Standard zonal harmonic acceleration using Earth `J2` | `lunalink.orbit` |
| F-GEO-001 | Elevation | ENU projection with `atan2(up,horizontal)` | `lunalink.frames` |
| F-FRAME-001 | ECI to ECEF | Passive Earth rotation `R3(theta0 - omega_E*t)` | `lunalink.frames` |
| F-EPS-001 | Array power | `P = flux*A*eta*pointing*conditioning*incidence`; `incidence = 1` for sun-tracking or `max(0,n_array dot s_hat)` for fixed-array mode | `lunalink.eps` |
| F-EPS-002 | Battery update | Trapezoidal net power integration with charge/discharge efficiency | `lunalink.eps` |
| F-TTC-001 | FSPL | `L_fs = 20*log10(4*pi*R/lambda)` | `lunalink.ttc` |
| F-TTC-002 | Antenna gain | `G = 10*log10(eta*(pi*D/lambda)^2)` | `lunalink.ttc` |
| F-TTC-003 | Link margin | `C/N0 = EIRP + G/T - losses + 228.6`; `margin = Eb/N0 - required Eb/N0` | `lunalink.ttc` |
| F-TCS-001 | Radiation | `Q_rad = epsilon*sigma*A*(T^4 - T_sink^4)` | `lunalink.thermal` |
| F-TCS-002 | External thermal node | `C*dT/dt = Q_solar + Q_albedo + Q_IR + Q_cond - Q_rad` | `lunalink.thermal` |
| F-ADCS-001 | Quaternion update | Unit quaternion propagation using angular-rate increment | `lunalink.adcs` |
| F-ADCS-002 | Magnetic torque | `T = m x B` with bounded commanded dipole | `lunalink.adcs` |
| F-ADCS-003 | Euler rigid body | `I*omega_dot = tau - omega x (I*omega)` | `lunalink.adcs` |
| F-TRADE-001 | Latin Hypercube | Stratified uniform sampling per parameter | `lunalink.trades` |

The formulas are intended for preliminary engineering analysis. External
correlation and uncertainty review are required before using results as formal
design acceptance evidence.
