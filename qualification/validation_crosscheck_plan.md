# External Validation Cross-Check Plan

## Objective

Compare LunaLink orbit and contact outputs against independent GMAT or Orekit
scenario runs before using the tool for formal decisions.

## Planned Cross-Checks

| Check | LunaLink output | External output | Acceptance approach |
| --- | --- | --- | --- |
| Initial orbit elements | `assumptions.json` | GMAT/Orekit scenario state | Exact configuration match |
| Orbit period | validation metric | Propagated external period | Tolerance set by project authority |
| Altitude envelope | `mission_timeseries.csv` | External ephemeris | Compare min/max and time history |
| Ground contact windows | `ttc_timeseries.csv` | External access report | Compare start/end times |
| Eclipse samples | `mission_timeseries.csv` | External eclipse report | Compare event timing |
| ECI/ECEF frame | `mission_timeseries.csv` | Orekit/GMAT frame transform | Compare sub-satellite longitude trend |
| Link budgets | `ttc_timeseries.csv` | Independent spreadsheet/DESCANSO-style budget | Compare C/N0, Eb/N0, margin |

## Current Status

The tool exports GMAT/Orekit-style scenario seeds under `scenario_exports/`.
Formal external execution and difference reports remain open certification tasks.
