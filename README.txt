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
  Dark space "mission control" theme (with a light toggle). Home screen with a
  live 3D globe, a subsystem status board, one tab per subsystem (Orbit, EPS,
  TCS, ADCS, TT&C, Evidence), and a Spacecraft tab with a SpaceX-style WebGL
  explorer of the LunaLink bus (exploded view, part info). First load runs the
  36 h mission once (~50 s, shown by an orbit animation) then caches it.

Deploy to the web:
  See DEPLOY.md (push to GitHub, then share.streamlit.io -> code/main_gui.py).

Run verification:
  .venv/bin/ruff check code
  MPLCONFIGDIR=.cache/matplotlib .venv/bin/python -m pytest -q

Notes:
  The tool is a preliminary NASA/ECSS-inspired engineering simulator for the
  Project X brief. It is not flight-qualified or certified. Certification use
  would require independent validation, IV&V, and authority acceptance.
