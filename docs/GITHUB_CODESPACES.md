# Run TechPulse in GitHub Codespaces

This guide starts the Streamlit app inside a GitHub Codespace with its own PostgreSQL database. A Codespace does not include the PostgreSQL database from your computer, and the project does not commit database credentials or populated database files.

> **Simulation notice:** The presentation-ready Simulation mode uses generated profiles and generated activity, adoption, sentiment, labels and model outputs. It is for demonstrating the workflow; it is not evidence about the real named technologies, actual company adoption, developer sentiment, or Kenya. The separate Research mode may show empty or blocked evidence states.

## 1. Create the Codespace

1. Open the TechPulse repository on GitHub.
2. Select **Code → Codespaces → Create codespace on `codex/techpulse-presentation-ready`**. If GitHub has a newer default branch, choose the branch containing this guide and deck.
3. Wait for the Codespace to finish building, then open its terminal.

## 2. Install and start PostgreSQL

Run in the Codespace terminal:

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo service postgresql start
pg_isready
```

Create a dedicated database and application role. Choose a strong URL-safe password and keep it private:

```bash
sudo -u postgres psql
```

At the `psql` prompt, enter:

```sql
CREATE ROLE techpulse_sim_app LOGIN;
\password techpulse_sim_app
CREATE DATABASE techpulse_sim OWNER techpulse_sim_app;
\q
```

The `\password` command prompts you privately; it avoids putting the password in shell history or the SQL command.

## 3. Install Python dependencies and configure the connection

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
nano .env
```

In `.env`, set `DATABASE_URL` to the dedicated Codespace database, replacing the placeholder with the password you just created:

```dotenv
DATABASE_URL=postgresql+psycopg2://techpulse_sim_app:YOUR_URL_SAFE_PASSWORD@localhost:5432/techpulse_sim
```

Keep `.env` private. It is ignored by Git. Save and exit nano with **Ctrl+O**, **Enter**, then **Ctrl+X**. Restrict its permissions:

```bash
chmod 600 .env
```

If the password contains reserved URL characters, percent-encode them in `DATABASE_URL`; choosing a strong password using only letters and numbers avoids that extra step.

## 4. Initialize the simulation database (first run only)

Run the reproducible pipeline once in this new database:

```bash
python -m src.db.migrate
python -m src.run_all
```

This applies versioned migrations, generates and loads the configured simulation, creates features and labels, and runs the grouped model experiment. It may take several minutes. The app requires the resulting PostgreSQL tables and saved model outputs; it does not silently substitute CSV files. Do not rerun the full experiment every time you start Streamlit.

## 5. Start the app

For each Codespace session, start PostgreSQL and Streamlit:

```bash
sudo service postgresql start
source .venv/bin/activate
python -m streamlit run dashboard/app.py --server.address 0.0.0.0 --server.port 8501
```

When Codespaces prompts about port **8501**, choose **Open in Browser**. If the prompt does not appear, open the **Ports** panel and follow the forwarded link for port 8501. Leave the terminal process running while presenting.

A stopped Codespace normally preserves its workspace and database files. If you rebuild or delete the Codespace, its PostgreSQL data may be lost; repeat the first-run initialization for a fresh database. Do not create or commit a database dump as a shortcut.

## Troubleshooting

- **Connection refused / database unavailable:** start PostgreSQL with `sudo service postgresql start`, check `pg_isready`, then verify the database name, role, password and port in `.env`.
- **Authentication failed:** reset the role password with `sudo -u postgres psql` followed by `\password techpulse_sim_app`, then update the private `.env` URL.
- **Simulation tables or model results missing:** run `python -m src.db.migrate` and `python -m src.run_all` against the dedicated `techpulse_sim` database. This is the first-run initialization step and can take several minutes.
- **Streamlit page is blank or inaccessible:** confirm the terminal still shows Streamlit running on port 8501 and open that port from the Codespaces **Ports** panel.
- **App opens in Research mode:** use the sidebar **Data mode** selector and explicitly choose **Simulation · PostgreSQL** for the generated demonstration.
- **Prediction missing for a technology:** saved held-out predictions exist only for some simulated profiles. The app does not invent a live prediction when one is absent.

## Presentation files

The annotated PowerPoint walkthrough is [TechPulse_Demo_Walkthrough.pptx](final_presentation/TechPulse_Demo_Walkthrough.pptx). It identifies the demo profile selection rule, shows the app click path, and labels the actual saved model metrics and simulation limitations.
