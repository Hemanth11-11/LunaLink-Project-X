#!/usr/bin/env bash
# LunaLink — one command to install dependencies and launch the dashboard.
#   Usage:  bash run.sh          # installs (first run) and opens the GUI
#           bash run.sh sim      # runs the headless simulation instead
set -e
cd "$(dirname "$0")"

# Create the virtual environment on first run (Python 3.13 preferred).
if [ ! -x ".venv/bin/python" ]; then
  (python3.13 -m venv .venv 2>/dev/null) || python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip >/dev/null
  .venv/bin/pip install -r code/requirements.txt
fi

export MPLCONFIGDIR=".cache/matplotlib"
if [ "$1" = "sim" ]; then
  exec .venv/bin/python code/main_simulation.py --out outputs/baseline
else
  exec .venv/bin/streamlit run code/main_gui.py
fi
