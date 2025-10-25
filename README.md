# Basketball Analytics (Simple Web UI)

This small Flask app provides a simple interface to tally in-game events per player and compute a set of derived metrics (simplified PER, True Shooting %, Assist/Turnover, Usage, BPM placeholder). It is intentionally lightweight so you can run locally and adapt it to your tracking workflow.

Features

- Add players
- Record events per player: shots (layup/midrange/3pt, contested), assists, turnovers, rebounds, strike-zone passes, cuts, paint touches, defensive contested/uncontested
- Per-player metrics and a team report page
- Export a CSV summary

Run locally

1. Create a virtualenv (recommended) and install requirements:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Run the app:

```bash
python app.py
```

Open http://127.0.0.1:5000 in your browser.

Notes and next steps

- The metrics are simplified proxies (not official PER/BPM implementations). If you want exact formulas (accounting for league pace, minutes, FTA, etc.), I can extend the model and UI.
- The app now saves tallies to a local file `data.json` automatically when you add players or record events. That means if you deploy the app to a server with a persistent disk the data will be saved there and the coach can access the same link and see the records.
- IMPORTANT: Not all hosting services treat the application filesystem as persistent. Some platforms (for example older free-tier Heroku dynos) provide ephemeral filesystems where files are removed when the container restarts or the app is redeployed. For reliable cloud persistence you should use one of these options:
  1.  Deploy to a provider that supports persistent disks (or attach a managed database). Render, Railway, and Fly all support easy deployments; for guaranteed persistence use a managed Postgres or an attached persistent disk.
  2.  Use a managed database (Postgres, Supabase, Firebase) — I can modify the app to store data there for robust persistence.
- I can add CSV import, per-game sessions, and printable tally sheets if you want.

Database / deployment notes (Postgres / Supabase)

- The app now supports a DATABASE_URL environment variable. If you set DATABASE_URL to a Postgres connection string (supplied by Supabase or Render Postgres) the app will persist data there.
- For local testing it falls back to sqlite (file `data.db`).

Render + Postgres quick steps

1. Push this repo to GitHub.
2. Create a Web Service on Render and connect the GitHub repo.
3. Create a Postgres database on Render (or create a free Supabase project) and copy the DATABASE_URL.
4. In Render's Web Service settings add an environment variable `DATABASE_URL` with the connection string.
5. Deploy. The public URL will be created by Render and the app will persist data to Postgres.

Security

- Do NOT commit your DATABASE_URL to GitHub. Use environment variables on the host.

Deployment notes

- I added a `Procfile` and `gunicorn` to `requirements.txt` so the app is ready for typical PaaS deployment.
- Basic flow to publish a shareable link (Render example):
  - Create a GitHub repo with this project and push the code.
  - Create a new Web Service on Render, connect the GitHub repo, and deploy; use the default build command and `gunicorn app:app` as the start command (Procfile handles this).
  - If you need persistent storage across restarts, add a managed Postgres database on Render and I can update the app to use it.

If you'd like I can:

- Implement direct Postgres (or Supabase) persistence now and update the code and README with deploy steps.
- Or implement server-side JSON + instructions and help you deploy to Render and confirm persistence on that platform.
