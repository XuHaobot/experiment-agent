"""
ResearchOS Server Launcher
Usage:
    python run_server.py
"""
import sys
from pathlib import Path
import uvicorn

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    print(f"Starting ResearchOS on http://0.0.0.0:5001 (Root: {ROOT})")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=5001, reload=False, access_log=True)
