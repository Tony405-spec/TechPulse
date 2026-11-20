# Run the new TechPulse app in GitHub Codespaces

The current app on `main` is the presentation-ready PostgreSQL Streamlit app. It is not the older SQLite demo. Codespaces uses a Linux development container even if you open it from a Windows computer, so do not run Windows PowerShell commands or enter a Windows/PostgreSQL password at a Linux `sudo` prompt.

> **Research integrity:** The app’s Simulation mode uses generated technology profiles, activity, enterprise events, survey-like values, labels and model results. These demonstrate the software workflow; they are not verified facts about the named technologies, companies, developers, or Kenya. The Research mode is separate and may report missing or blocked evidence.

## Recommended: create a fresh Codespace after the update merges

1. Open the repository on GitHub and select branch **`main`**.
2. Choose **Code → Codespaces → Create codespace on main**.
3. Wait for the first setup to finish. The repository’s dev-container configuration automatically:
   - starts a private PostgreSQL service for this Codespace;
   - installs the Python requirements;
   - applies the database migrations and runs the deterministic simulation pipeline if the database is empty; and
   - starts Streamlit and forwards port **8501**.
4. When GitHub offers the forwarded port, click **Open in Browser**. If it does not open automatically, use the Codespaces **Ports** panel and open **TechPulse Streamlit (8501)**.

The initial build and model run can take several minutes. Keep the Codespace open while it prepares. No `sudo`, local Windows PostgreSQL service, `.env` edit, or password is needed for this Codespaces setup.

## Update an existing Codespace on `main`

In its terminal, run:

```bash
git pull origin main
```

Then open the Command Palette with **Ctrl+Shift+P**, run **Codespaces: Rebuild Container**, and wait for the setup to finish. The new configuration is only applied after the rebuild. Then open forwarded port **8501**.

## Start Streamlit manually

The configured Codespace starts the app automatically. If you need to start it yourself, use the Codespace terminal (Linux shell):

```bash
cd /workspaces/TechPulse
source .venv/bin/activate
python -m streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port 8501
```

Do not run `sudo -u postgres psql` here. PostgreSQL is already running as a separate, private Codespaces service. The disposable database is not exposed as a forwarded port and is intended only for this development demonstration, not production use.

## If setup or the app fails

- **Setup still running:** check the Codespaces build/setup output; the first-time dependency install and model training are expected to take several minutes.
- **Port 8501 is not open:** use the Ports panel. If the app is stopped, run the manual Streamlit command above.
- **Database connection error:** use **Codespaces: Rebuild Container** so the private PostgreSQL service starts with the app container. Do not paste a password into the `sudo` prompt.
- **No saved prediction for a selected technology:** the app only shows persisted held-out predictions; it does not create an unsupported live prediction.
- **Research pages are empty or blocked:** select **Simulation · PostgreSQL** for the generated demonstration. Research evidence remains separate.

## Presentation files

The [annotated walkthrough](final_presentation/TechPulse_Demo_Walkthrough.pptx) shows the click path, selected demo examples, actual saved simulation metrics and limitations. Familiar technology names in Simulation mode are display labels attached to generated profiles; they do not make the simulated histories real-world evidence.