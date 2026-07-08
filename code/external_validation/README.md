# External validation (SPICE + Orekit)

These scripts independently cross-check the LunaLink models against NASA/NAIF
SPICE and Orekit. They are **not** part of the runtime and are **not** in
`requirements.txt` — the tool installs and runs cleanly with `pip` without them.
They document how the numbers in
`outputs/baseline/external_validation/spice_orekit_crosscheck.md` were produced.

## Reproduce

Reference tools run in a separate environment (they downgrade `numpy`, and Orekit
needs a JVM), so keep them out of the project venv:

```bash
# 1. Reference environment (Python 3.13)
python -m venv /tmp/refvenv
/tmp/refvenv/bin/pip install numpy pandas scipy spiceypy orekit_jpype

# 2. A JRE/JDK 17+ on PATH or JAVA_HOME (Temurin works)

# 3. SPICE generic kernels into ./spice/ :
#    naif0012.tls, de440s.bsp, pck00011.tpc  (naif.jpl.nasa.gov/pub/naif/generic_kernels)
# 4. orekit-data.zip  (gitlab.orekit.org/orekit/orekit-data)

# 5. Export the tool's outputs (project venv), then run the check (ref venv):
<project-venv>/bin/python export_tool_truth.py
JAVA_HOME=/path/to/jdk /tmp/refvenv/bin/python spice_orekit_crosscheck.py
```

Paths at the top of each script may need adjusting to your machine. The scripts
import the tool's **real** analytic Sun/Moon functions (via `PYTHONPATH`) so they
validate the shipped code, not a copy.
