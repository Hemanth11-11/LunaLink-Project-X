# Dashboard Smoke Test

## Result

Pass on 2026-07-07.

## Command

```bash
env MPLCONFIGDIR=/tmp/lunalink-mpl-cache HOME=/home/godspeed/Downloads/Project\ X .venv/bin/streamlit run code/main_gui.py --server.headless true --server.address 127.0.0.1 --server.port 8504
```

## Evidence

Streamlit started successfully and reported:

```text
Uvicorn server started on 127.0.0.1:8504
URL: http://127.0.0.1:8504
```

The server is intended to remain running while the dashboard is inspected.
