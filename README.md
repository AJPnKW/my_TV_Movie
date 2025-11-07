## Deploy/Run

### GitHub Pages (no server)
1. Add repo secrets: `API_TMDB_KEY` (required), `API_TMDB_TOKEN` (optional).
2. Ensure the workflow exists at `/.github/workflows/build-data.yml`.
3. Run the workflow from the Actions tab (or wait for the daily schedule).
4. Visit: https://ajpnkw.github.io/my_TV_Movie/  
   (Root `/index.html` redirects to `/web/index.html`.)

### Local (optional)
- `run_server.bat` creates a venv, builds `data/data.json`, and can run Flask via `app.py`.
- Local URL: `http://<YOUR_PC_IP>:8811/` (only if you run Flask).
