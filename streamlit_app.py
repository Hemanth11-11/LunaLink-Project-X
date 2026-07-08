"""Streamlit Community Cloud entry point.

Streamlit Cloud looks for ``streamlit_app.py`` at the repository root by default.
This shim adds ``code/`` to the path and launches the LunaLink dashboard, so the
app deploys with the default main-file setting (no ``code/`` prefix required).
Running ``streamlit run code/main_gui.py`` directly still works too.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "code"))

from main_gui import main  # noqa: E402

main()
