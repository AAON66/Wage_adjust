$env:PYTHONPATH = (Resolve-Path ".").Path
& ".\.venv\Scripts\python.exe" -m uvicorn backend.app.main:app --reload
