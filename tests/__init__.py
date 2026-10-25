import sys
from pathlib import Path

# Ensure src/ layout is importable during test discovery without requiring manual PYTHONPATH
src_dir = str(Path(__file__).resolve().parent.parent / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)
