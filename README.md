# SHEild — Website + Danger Prediction Engine (Single URL Deploy)

## Deploy on Render
1) Create a new **Web Service** from this repo/zip.
2) Set **Environment Variables**:
   - `DPE_API_KEY` = `dev-key` (change later for production)
3) Deploy.

- Frontend served at `/` (from `/static/index.html`).
- Backend API at `/api/...`.

## Local run
```bash
python -m venv .venv
# Windows
.\.venv\Scriptsctivate
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
set DPE_API_KEY=dev-key           # Windows PowerShell: $env:DPE_API_KEY="dev-key"
python app.py
# http://localhost:8000
```
