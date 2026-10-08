# One-shot setup + run for AirCast India (Windows PowerShell)
$ErrorActionPreference = "Stop"
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m ml.ingest
.\.venv\Scripts\python -m ml.clean
.\.venv\Scripts\python -m ml.features
.\.venv\Scripts\python -m ml.train
.\.venv\Scripts\python -m ml.explain
Start-Process powershell -ArgumentList "-NoExit","-Command",".\.venv\Scripts\uvicorn backend.main:app --port 8000"
Set-Location frontend; npm install; npm run dev
