"""Static checks for PowerShell embedded in the tooling; hosts run Windows PowerShell 5.1."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# PowerShell 5.1's ConvertFrom-Json writes a JSON array to the pipeline as ONE object, so wrapping the pipeline in
# @(...) yields a one-element array that holds the whole array. Two real failures: the G25 host probe's key-path
# inventory and an operator wait loop that never saw its step finish. Assign the result first, then enumerate it.
WRAPPED_CONVERT = re.compile(r"@\([^()]*\|\s*ConvertFrom-Json\b[^()]*\)", re.IGNORECASE)


class PowerShellSnippetTests(unittest.TestCase):
    def test_pattern_detects_the_wrapped_pipeline(self):
        self.assertTrue(WRAPPED_CONVERT.search("$rows=@(Get-Content $p -Raw | ConvertFrom-Json)"))
        self.assertIsNone(WRAPPED_CONVERT.search("$rows=Get-Content $p -Raw | ConvertFrom-Json; @($rows)"))

    def test_no_convertfrom_json_pipeline_is_wrapped_in_an_array_subexpression(self):
        hits = [f"{path.relative_to(ROOT)}:{text.count(chr(10), 0, match.start()) + 1}"
                for folder in ("scripts", "omp_strata", "eval")
                for path in sorted((ROOT / folder).rglob("*")) if path.suffix in {".py", ".ps1", ".psm1"}
                for text in [path.read_text(encoding="utf-8", errors="replace")]
                for match in WRAPPED_CONVERT.finditer(text)]
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
