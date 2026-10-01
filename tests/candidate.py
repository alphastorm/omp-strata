"""The candidate profile the suite exercises: `OMP_STRATA_PROFILE` (exported by `dev-env`), else the current one."""

from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CURRENT = "win11-rtx5090-coder-iq1m-131k-strata0.1.30-omp18.4.6"
PROFILE = Path(os.environ.get("OMP_STRATA_PROFILE") or REPO / "profiles" / f"{CURRENT}.json").resolve()
CANDIDATE = PROFILE.stem
