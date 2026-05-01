@echo off
if "%1"=="--bot" (
    curl -s -H "Accept: application/json" http://127.0.0.1:8000/fact/%2
) else (
    python.exe -m uvicorn pysrc.web.server:app --reload
)
