import sys
from pathlib import Path

# Ensure the inner project package path is available when launching from outer workspace root.
BASE_DIR = Path(__file__).resolve().parent / "cv_builder_automation"
if BASE_DIR.exists():
    sys.path.insert(0, str(BASE_DIR))
else:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from apps.api.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)