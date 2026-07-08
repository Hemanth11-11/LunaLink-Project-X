LunaLink Engineering Simulator - Project X

Clean install:
  python3.13 -m venv .venv
  .venv/bin/pip install -r code/requirements.txt

Run headless simulation:
  MPLCONFIGDIR=.cache/matplotlib .venv/bin/python code/main_simulation.py --out outputs/baseline

Build reports:
  .venv/bin/python report/build_report.py --evidence outputs/baseline --out report/LunaLink_Baseline_Report.md
  MPLCONFIGDIR=.cache/matplotlib .venv/bin/python report/build_pdf_report.py --evidence outputs/baseline --out report/LunaLink_Final_Report.pdf

Launch GUI (interactive dashboard):
  .venv/bin/streamlit run code/main_gui.py
  Opens on a mission Home screen with a live 3D globe (textured Earth/Moon) and
  a subsystem status board, plus one tab per subsystem (Orbit, EPS, TCS, ADCS,
  TT&C, Evidence). First load runs the 36 h mission once (~30 s) then caches it.

Run verification:
  .venv/bin/ruff check code
  MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q

Notes:
  The tool is a preliminary NASA/ECSS-inspired engineering simulator for the
  Project X brief. It is not flight-qualified or certified. Certification use
  would require independent validation, IV&V, and authority acceptance.
