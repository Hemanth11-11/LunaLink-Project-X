# Deploying the LunaLink dashboard

The `Unable to deploy` message means the code is not yet on a GitHub remote.
Streamlit Community Cloud deploys **from a GitHub repository**, so publish first.

## 1. Publish to GitHub (one time)

The repo is already initialised and committed locally with a `.gitignore` that
excludes `.venv/`, caches and scratch files. Create an empty repo on GitHub
(no README/licence), then:

```bash
cd "Project X"
git remote add origin https://github.com/<you>/lunalink.git
git branch -M main
git push -u origin main
```

## 2. Deploy on Streamlit Community Cloud

1. Go to https://share.streamlit.io → **New app**.
2. Pick the repo, branch `main`, and **main file** `code/main_gui.py`.
3. Advanced settings → Python **3.13**.
4. Deploy.

Community Cloud reads `code/requirements.txt` to build the environment
(`ppigrf` and `itur` are optional; the app degrades gracefully without them, and
`Orekit`/`SPICE` are **not** runtime dependencies).

## 3. Cloud tuning (recommended)

Community Cloud has ~1 GB RAM and no GPU. The 3D WebGL runs client-side (fine),
but the first mission run is ~50 s. To speed the cold start there, set the
sidebar **Output time step** to 600 s (default) or add a smaller default.

## Alternatives

- **Hugging Face Spaces** (Streamlit template) — same repo, similar steps.
- **Local / LAN**: `streamlit run code/main_gui.py` then open the Network URL.
- **Temporary public link**: `ngrok http 8501` while the app runs locally.

The submission zip for Moodle is separate from deployment: it is just
`/code`, `/report`, `/assets`, `README.txt` (exclude `.venv/` and `outputs/` if
size matters — the bundle is well under the 50 MB limit either way).
