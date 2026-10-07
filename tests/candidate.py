"""The candidate profile the suite exercises: `OMP_STRATA_PROFILE` (exported by `dev-env`), else the current one,
and which upstream fixes its pinned components carry."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CURRENT = "win11-rtxpro6000-iq3s-131k-strata0.1.40.2-omp18.8.0"
PROFILE = Path(os.environ.get("OMP_STRATA_PROFILE") or REPO / "profiles" / f"{CURRENT}.json").resolve()
CANDIDATE = PROFILE.stem


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("."))


_PINS = json.loads(PROFILE.read_text(encoding="utf-8"))
# Strata#211/#231 (v0.1.31): an announced tool call the output ends inside stays unfinished - its JSON is not closed
# and the answer does not end in "tool_calls". Earlier releases closed the JSON and reported a complete call.
STRATA_REPORTS_UNFINISHED_CALLS = _version(_PINS["strata"]["engine_version"]) >= (0, 1, 31)
# can1357/oh-my-pi#13868 (18.4.10): a tool call whose argument JSON is cut off gets the parse error instead of running.
OMP_REFUSES_UNFINISHED_CALLS = _version(_PINS["omp"]["version"]) >= (18, 4, 10)


def expected_failure_unless(fixed: bool):
    """A test of a known upstream defect fails as expected until the pinned components carry the fix."""
    return (lambda test: test) if fixed else unittest.expectedFailure
