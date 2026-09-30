"""Intentionally regenerate the evaluation identity BEFORE a scored batch, never during one."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eval.support import EVAL, canonical, digest, files, hashes, inventory, materialize, tree_hash, visible_status

BUDGET = {"wall_seconds": 900, "tool_calls": 40, "max_output_tokens_per_response": 32768,
          "total_output_tokens": 131072, "max_event_bytes": 33554432, "max_stderr_bytes": 1048576}
TASKS = [("bugfix-a", "ordinary-bugfix"), ("bugfix-b", "ordinary-bugfix"),
         ("multifile-regression", "multifile-regression"), ("tool-loop", "tool-heavy-loop"),
         ("long-context", "long-context-retrieval"), ("continuation", "restart-continuation")]


def main():
    tasks = []
    with tempfile.TemporaryDirectory(prefix="eval-freeze-") as temporary:
        for name, category in TASKS:
            task = {"id": name, "category": category, "budget": BUDGET.copy(),
                    "phases": 2 if name == "continuation" else 1}
            workspace = materialize(task, Path(temporary) / name, git=False)
            immutable = {}
            removable = []
            for path in files(workspace):
                relative = path.relative_to(workspace).as_posix()
                if relative.startswith(("tests/", "docs/", "examples/", "phase1/")) or relative == "sku.py":
                    immutable[relative] = digest(path.read_bytes())
                if relative.startswith("phase1/"):
                    removable.append(relative)
            verifier = EVAL / "verifiers" / name
            (verifier / "immutable.json").write_bytes(canonical({"files": immutable,
                                      "removable_between_phases": removable}) + b"\n")
            source = EVAL / "tasks" / name
            prompts = {path.name: digest(path.read_bytes()) for path in source.glob("*.md")}
            chars = sum(len(path.read_text(encoding="utf-8")) for path in files(workspace))
            task.update(workspace_sha256=tree_hash(workspace), seed_tree_sha256=tree_hash(source / "workspace"),
                        prompt_sha256=digest(canonical(prompts)), verifier_sha256=tree_hash(verifier),
                        reference_sha256=tree_hash(EVAL / "reference" / name),
                        preexisting_visible_tests=visible_status(workspace),
                        workspace_size={"files": len(files(workspace)), "chars": chars,
                                        "estimated_tokens_chars_div_4": chars / 4},
                        immutable_files=sorted(immutable), remove_between_phases=removable)
            if name == "long-context":
                task.update(generated_sha256=tree_hash(workspace / "docs"), generator="eval/generate_corpus.py",
                            generator_seed=6042042, real_tokenizer_measurement="not_run")
                if not 60000 <= chars / 4 <= 80000:
                    raise ValueError("long-context corpus is outside the 60-80K chars/4 estimate")
            tasks.append(task)
    manifest = {"schema_version": 1, "evaluation_version": "synthetic-1", "attempts_per_task": 3,
                "batch_wall_seconds": 16200,
                "order": "round-robin over the frozen task order, then next attempt number",
                "hash_contract": "sha256 of canonical UTF-8 JSON {relative POSIX path: sha256(bytes)}; sorted keys, compact separators",
                "tasks": tasks, "files": inventory()}
    (EVAL / "tasks.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"frozen": len(tasks), "sizes": {task["id"]: task["workspace_size"] for task in tasks}}))


if __name__ == "__main__":
    main()
