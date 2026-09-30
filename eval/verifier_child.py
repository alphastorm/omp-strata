"""External test interpreter entry point; -I/-B prevent ambient path and bytecode writes."""
import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path

hidden, workspace = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(workspace))
spec = importlib.util.spec_from_file_location("immutable_hidden_tests", hidden)
module = importlib.util.module_from_spec(spec)
module.WORKSPACE = workspace
spec.loader.exec_module(module)
loader = unittest.TestLoader()
suite = unittest.TestSuite([loader.loadTestsFromModule(module), loader.discover(str(workspace / "tests"))])
output = io.StringIO()
result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
print(json.dumps({"completed": True, "tests_run": result.testsRun, "failures": len(result.failures),
                  "errors": len(result.errors), "output": output.getvalue()}))
raise SystemExit(0 if result.wasSuccessful() and result.testsRun else 1)
