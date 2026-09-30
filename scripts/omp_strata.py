#!/usr/bin/env python3
"""Lifecycle tool for one stock OMP + stock Strata candidate: validate/fetch/install/start/status/stop/launch-omp."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from omp_strata.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
