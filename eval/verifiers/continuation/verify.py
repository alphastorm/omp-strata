"""Run the immutable verifier outside the candidate workspace."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from verifier_support import main

if __name__ == "__main__":
    raise SystemExit(main(Path(__file__).resolve().parent))
