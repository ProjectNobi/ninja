"""KS42 test-gated repair + polish tests — executes the gate, does not grep it.

KS42 restores two things KS39 removed and the current king still runs: repair
adoption gated on a real test outcome, and a polish pass on an already-clean
patch. The gate is the load-bearing part. KS39 adopted a "coverage" repair
unconditionally, so a structurally fuller but functionally wrong revision could
replace a correct fix -- the shape of the 0.250 loss round, where a 412-line
patch was complete-looking and simply wrong.

The fall-open property matters as much as the gate: on a TypeScript or PHP repo
no Python test is runnable, _python_test_outcome returns "none", and adoption
degrades to exactly KS39's structural checks. Never worse, sometimes better.

Stdlib only, no network. Kept under tests/ so it never enters the submission
bundle. Run:  python3 -m unittest tests.test_ks42_repair_gate -v
"""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_FILE = os.environ.get(
    "AGENT_FILE", os.path.join(_REPO_ROOT, "agent_cl_gpt_KingSlayer42.py"))


def _load():
    name = f"ks42_{len(sys.modules)}"
    spec = importlib.util.spec_from_file_location(name, _AGENT_FILE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True)


def _patch_for(paths):
    """Minimal unified-diff header; _changed_paths only reads `+++ b/` lines."""
    return "".join(f"--- a/{p}\n+++ b/{p}\n@@ -1 +1 @@\n-old\n+new\n" for p in paths)


class TestStaticIntegrity(unittest.TestCase):
    def test_no_undefined_module_names(self):
        """A `sys.executable` with no `import sys` compiles fine and dies at runtime.
        Symptom that motivated this test: the reroll raised NameError on its first
        real invocation and the round timed out to 0.000."""
        with open(_AGENT_FILE) as fh:
            tree = ast.parse(fh.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update((a.asname or a.name).split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.update(a.asname or a.name for a in node.names)
        stdlib = {"sys", "os", "re", "json", "time", "subprocess", "traceback",
                  "shutil", "tempfile", "ast", "signal", "urllib", "difflib"}
        used = {n.value.id for n in ast.walk(tree)
                if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
        self.assertEqual(sorted((used & stdlib) - imported), [])

    def test_carries_no_reroll(self):
        """The king has never had a reroll. KS40 added one and regressed; it would
        have fired on neither of the two rounds that hold ~90% of the deficit."""
        with open(_AGENT_FILE) as fh:
            tree = ast.parse(fh.read())
        names = {n.name for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
        forbidden = [n for n in names if any(
            k in n.lower() for k in ("reroll", "best_of", "is_weak", "attempt2"))]
        self.assertEqual(forbidden, [])

    def test_wall_budget_leaves_a_return_path(self):
        mod = _load()
        self.assertLessEqual(mod._resolve_wall_clock(), 270.0)
        self.assertGreaterEqual(mod._WALL_CLOCK_RESERVE_SECONDS, 30.0)

    def test_solve_gates_adoption_on_the_test_outcome(self):
        """Pins the wiring. The adoption branch lives inside solve(), which needs a
        live model to execute, so a refactor could otherwise drop the gate and
        every other test here would still pass -- and adoption would silently
        return to KS39's unconditional `adopt = True` on a coverage repair.
        """
        with open(_AGENT_FILE) as fh:
            tree = ast.parse(fh.read())
        solve = next(n for n in tree.body
                     if isinstance(n, ast.FunctionDef) and n.name == "solve")

        calls = {n.func.id for n in ast.walk(solve)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertIn("_python_test_outcome", calls,
                      "solve() must run the test outcome before adopting a repair")
        self.assertIn("_build_polish_task", calls,
                      "solve() must run the polish pass on a clean patch")

        # The polish pass must be *triggered* by a clean patch, not merely defined.
        # Checking that _build_polish_task is called is not enough: a mutation that
        # replaces `if reason is None:` with `if False:` leaves the call reachable
        # in the kind == "polish" branch that can now never be entered.
        triggered = False
        for node in ast.walk(solve):
            if not isinstance(node, ast.If):
                continue
            t = node.test
            is_reason_none = (isinstance(t, ast.Compare)
                              and isinstance(t.left, ast.Name) and t.left.id == "reason"
                              and len(t.ops) == 1 and isinstance(t.ops[0], ast.Is)
                              and isinstance(t.comparators[0], ast.Constant)
                              and t.comparators[0].value is None)
            if not is_reason_none:
                continue
            for sub in ast.walk(node):
                if (isinstance(sub, ast.Constant) and sub.value == "polish"):
                    triggered = True
        self.assertTrue(triggered,
                        "a clean patch (reason is None) must escalate to a polish pass")

        # Every `adopt = ...` must consult rtest; none may be a bare True.
        adopts = [n for n in ast.walk(solve) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == "adopt" for t in n.targets)]
        self.assertTrue(adopts, "no adopt decision found in solve()")
        for node in adopts:
            names = {c.id for c in ast.walk(node.value) if isinstance(c, ast.Name)}
            self.assertIn("rtest", names,
                          f"adopt decision at line {node.lineno} ignores the test outcome")


class _RepoCase(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def _repo(self, files):
        d = tempfile.mkdtemp(prefix="ks42_")
        _git(d, "init", "-q")
        _git(d, "config", "user.email", "t@t")
        _git(d, "config", "user.name", "t")
        for rel, content in files.items():
            full = os.path.join(d, rel)
            os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(rel) else None
            with open(full, "w") as fh:
                fh.write(content)
        _git(d, "add", "-A")
        _git(d, "commit", "-qm", "base")
        return d


class TestPythonTestOutcome(_RepoCase):
    def test_passing_test_reports_pass(self):
        repo = self._repo({"src.py": "def f():\n    return 1\n",
                           "test_src.py": "from src import f\n\ndef test_f():\n    assert f() == 1\n"})
        self.assertEqual(self.mod._python_test_outcome(repo, _patch_for(["test_src.py"])), "pass")

    def test_failing_test_reports_fail(self):
        """The gate's whole purpose: a revision whose own test fails is wrong."""
        repo = self._repo({"src.py": "def f():\n    return 1\n",
                           "test_src.py": "from src import f\n\ndef test_f():\n    assert f() == 999\n"})
        self.assertEqual(self.mod._python_test_outcome(repo, _patch_for(["test_src.py"])), "fail")

    def test_no_test_touched_reports_none(self):
        repo = self._repo({"src.py": "def f():\n    return 1\n"})
        self.assertEqual(self.mod._python_test_outcome(repo, _patch_for(["src.py"])), "none")

    def test_non_python_test_reports_none_and_falls_open(self):
        """TypeScript/PHP repos -- both loss rounds -- must degrade to KS39, not error."""
        repo = self._repo({"src.ts": "export const f = () => 1;\n",
                           "src.test.ts": "test('f', () => expect(f()).toBe(1));\n"})
        self.assertEqual(self.mod._python_test_outcome(repo, _patch_for(["src.test.ts"])), "none")


class TestRepairReason(_RepoCase):
    def test_failing_test_yields_test_fail(self):
        repo = self._repo({"src.py": "def f():\n    return 1\n",
                           "test_src.py": "from src import f\n\ndef test_f():\n    assert f() == 999\n"})
        reason = self.mod._repair_reason(repo, _patch_for(["src.py", "test_src.py"]), issue_text="fix f")
        self.assertIsNotNone(reason)
        self.assertEqual(reason[0], "test_fail")

    def test_source_without_test_yields_no_test(self):
        repo = self._repo({"src.py": "def f():\n    return 1\n"})
        reason = self.mod._repair_reason(repo, _patch_for(["src.py"]), issue_text="fix f")
        self.assertIsNotNone(reason)
        self.assertEqual(reason[0], "no_test")

    def test_check_tests_false_skips_the_test_branches(self):
        """When too little wall remains to afford a 25s test run, the gate must
        not fire at all rather than block on a test it never ran."""
        repo = self._repo({"src.py": "def f():\n    return 1\n"})
        reason = self.mod._repair_reason(repo, _patch_for(["src.py"]),
                                         issue_text="fix f", check_tests=False)
        self.assertTrue(reason is None or reason[0] not in ("test_fail", "no_test"))

    def test_empty_patch_short_circuits_before_any_test_run(self):
        repo = self._repo({"src.py": "x=1\n"})
        reason = self.mod._repair_reason(repo, "", issue_text="fix")
        self.assertEqual(reason[0], "empty")


class TestPolishPromptExists(_RepoCase):
    def test_polish_task_is_distinct_from_repair_task(self):
        """KS39 removed the polish loop. The king that beat us runs it on an
        already-clean patch, which is where its extra top-bucket rounds plausibly
        come from: both agents correct, the king's answer fuller."""
        polish = self.mod._build_polish_task("do X", "reason")
        repair = self.mod._build_repair_task("do X", "reason")
        self.assertNotEqual(polish, repair)
        self.assertIn("do X", polish)
        self.assertIn("polish", polish.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
