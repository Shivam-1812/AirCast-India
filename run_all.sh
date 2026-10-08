#!/usr/bin/env bash
set -e
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m ml.ingest && python -m ml.clean && python -m ml.features && python -m ml.train && python -m ml.explain
uvicorn backend.main:app --port 8000 &
cd frontend && npm install && npm run dev
