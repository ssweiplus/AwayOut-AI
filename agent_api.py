from __future__ import annotations

import runpy
from pathlib import Path


if __name__ == "__main__":
    skill_api = Path(__file__).resolve().parent / "skills" / "awayout-security" / "api.py"
    runpy.run_path(str(skill_api), run_name="__main__")
