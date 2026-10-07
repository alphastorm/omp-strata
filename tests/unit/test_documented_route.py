"""QUICKSTART addresses, literal bytes and CLI/profile contracts stay usable without execution."""
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import documented_route as route

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "win11-rtx5090-coder-iq1m-131k.json"


class DocumentedRouteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / "profiles").mkdir()
        (self.root / "profiles" / PROFILE).write_bytes((ROOT / "profiles" / PROFILE).read_bytes())

    def doc(self, command, language="sh"):
        return f"# Route\n\n## Run\n```{language}\n{command}\n```\n"

    def test_heading_index_addresses_and_literal_crlf_hashes(self):
        text = '# Route\r\n## Run\r\n```sh\r\necho "first"  \r\n```\r\n```sh\r\necho second\r\n```\r\n'
        path = self.root / "quickstart.md"
        path.write_bytes(text.encode("utf-8"))
        blocks = route.parse_blocks(text)
        self.assertEqual([("Run", 0), ("Run", 1)], [(b.heading, b.index) for b in blocks])
        expected = b'echo "first"  \r\n'
        self.assertEqual(expected, route.extract(path, "Run", 0).text.encode("utf-8"))
        self.assertEqual(hashlib.sha256(expected).hexdigest(), blocks[0].sha256)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, route.main(["--list", "--doc", str(path)]))
        listed = json.loads(output.getvalue())
        self.assertEqual([0, 1], [item["index"] for item in listed])
        self.assertEqual(blocks[1].sha256, listed[1]["sha256"])

    def test_missing_duplicate_and_unclosed_headings_are_rejected(self):
        for text, error in (("```sh\necho x\n```\n", "no heading"),
                            ("## Run\n## Run\n", "duplicate heading"),
                            ("## Run\n```sh\necho x\n", "unclosed fence")):
            with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                route.parse_blocks(text)
        path = self.root / "quickstart.md"
        path.write_text(self.doc("echo x"), encoding="utf-8")
        for heading, index in (("Missing", 0), ("Run", 1)):
            with self.assertRaisesRegex(ValueError, "no fenced block"):
                route.extract(path, heading, index)

    def test_unknown_subcommand_and_bad_option_are_rejected(self):
        for tail in (f"imaginary --profile profiles/{PROFILE}",
                     f"doctor --profile profiles/{PROFILE} --imaginary",
                     f"start --profile profiles/{PROFILE} --timeout not-a-number"):
            with self.subTest(tail=tail):
                result = route.check(self.doc("python3 scripts/omp_strata.py " + tail), self.root)
                self.assertEqual(1, result["commands"])
                self.assertTrue(any("CLI arguments rejected" in e for e in result["errors"]), result)

    def test_missing_and_invalid_profile_references_are_rejected(self):
        for name, contents in (("missing.json", None), ("invalid.json", "{}")):
            if contents is not None:
                (self.root / "profiles" / name).write_text(contents, encoding="utf-8")
            result = route.check(self.doc(f"python3 scripts/omp_strata.py validate --profile profiles/{name}"), self.root)
            self.assertTrue(any(f"profiles/{name}: invalid or unavailable" in e for e in result["errors"]), result)
        text = self.doc(f"python3 scripts/omp_strata.py validate --profile profiles/{PROFILE}")
        result = route.check(text + "See `profiles/absent-in-prose.json`.\n", self.root)
        self.assertTrue(any("absent-in-prose.json" in e for e in result["errors"]))

    def test_powershell_variables_paths_comments_and_continuations_parse_without_dispatch(self):
        text = self.doc(f'$prof = "profiles\\{PROFILE}"\n$root = "$env:USERPROFILE\\runtime"\n'
                        'py -3 scripts\\omp_strata.py start `\n  --profile $prof --root $root # start comment',
                        "powershell")
        text += ('\n## OMP\n```powershell\n'
                 'py -3 "$env:USERPROFILE\\src\\omp-strata\\scripts\\omp_strata.py" launch-omp '
                 f'--profile "$env:USERPROFILE\\src\\omp-strata\\profiles\\{PROFILE}" '
                 '--root $root -- -p "Run tests and explain results."\n```\n')
        # If static validation ever dispatches, fail before any lifecycle or external program can run.
        with patch("omp_strata.cli.cmd_start", side_effect=AssertionError("dispatched start")), \
                patch("omp_strata.cli.cmd_launch_omp", side_effect=AssertionError("dispatched OMP")), \
                patch("subprocess.Popen", side_effect=AssertionError("spawned process")):
            result = route.check(text, self.root)
        self.assertEqual({"blocks": 2, "commands": 2, "profiles": 1, "errors": []}, result)

    def test_posix_assignment_and_continuation_parse(self):
        text = self.doc(f'prof="profiles/{PROFILE}"\npython3 scripts/omp_strata.py validate \\\n  --profile "$prof"')
        self.assertEqual([], route.check(text, self.root)["errors"])

    def test_undefined_or_reassigned_profile_variables_cannot_reuse_old_value(self):
        for prefix in ("", f'$prof = "profiles\\{PROFILE}"\n$prof = Get-Content private.txt\n'):
            text = self.doc(prefix + "py -3 scripts\\omp_strata.py validate --profile $prof", "powershell")
            self.assertTrue(any("literal profiles/*.json" in e for e in route.check(text, self.root)["errors"]))

    def test_each_command_on_a_compound_line_is_checked(self):
        text = self.doc(f"python3 scripts/omp_strata.py validate --profile profiles/{PROFILE}; "
                        f"python3 scripts/omp_strata.py nonsense --profile profiles/{PROFILE}")
        result = route.check(text, self.root)
        self.assertEqual(2, result["commands"])
        self.assertEqual(1, len(result["errors"]))

    def test_check_cli_returns_failure_for_real_document_defect(self):
        path = self.root / "quickstart.md"
        path.write_text(self.doc("python3 scripts/omp_strata.py nonsense"), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(1, route.main(["--check", "--doc", str(path), "--root", str(self.root)]))


if __name__ == "__main__":
    unittest.main()
