"""KS43 no-polish + token accounting tests — executes solve(), does not grep it.

KS42 turned a None from _repair_reason() (meaning: the patch is already clean)
into a "polish" sub-loop, so an already-correct patch cost two full model runs.
KS43 ends the task instead. These tests drive solve() with _run_loop stubbed to
a counter, so the assertion is on observed model-run count, not on source text.

The KS42-vs-KS43 comparison is the load-bearing test: the same clean-patch
scenario must cost 2 runs on KS42 and 1 on KS43. Everything else could pass on a
file that merely deleted the function and left the call site intact.

Stdlib only, no network. Kept under tests/ so it never enters the submission
bundle. Run:  python3 -m unittest tests.test_ks43_no_polish -v
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_KS43 = os.path.join(_REPO_ROOT, "agent_cl_gpt_KingSlayer43.py")
_KS42 = os.path.join(_REPO_ROOT, "agent_cl_gpt_KingSlayer42.py")

_PATCH = "--- a/src/x.py\n+++ b/src/x.py\n@@ -1 +1 @@\n-old\n+new\n"


def _load(path):
    name = f"agent_{os.path.basename(path)}_{len(sys.modules)}"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _neutralise(mod):
    """Stub everything solve() touches except the repair/polish decision."""
    mod._resolve_inference_config = lambda *a, **k: ("model", "http://local", "tok")
    mod._resolve_wall_clock = lambda: 300.0
    mod._build_repo_summary = lambda p: ""
    mod._issue_named_context = lambda i, p: ""
    mod._existing_issue_files = lambda i, p, limit=0: []
    mod._api_route_context = lambda i, p, exclude=None: ""
    mod._cpp_config_context = lambda i, p, paths: ""
    mod._repo_paths = lambda p: []
    mod._collect_repo_patch = lambda p: _PATCH
    mod._tree_has_changes = lambda p: True
    mod._syntax_errors = lambda p, t: []
    mod._patch_acceptable = lambda t: True
    mod._python_test_outcome = lambda p, t: "pass"
    mod._source_files = lambda t: set()
    mod._added_test_files = lambda t: set()


def _counting_run_loop(mod, calls, tokens=(0, 0)):
    def stub(config, task):
        calls.append(task)
        kw = dict(success=True, patch=_PATCH, logs="", steps=1, cost=None,
                  message="ok", exit_status="Submitted", transcript=[])
        if "prompt_tokens" in mod.RunOutcome.__dataclass_fields__:
            kw["prompt_tokens"], kw["completion_tokens"] = tokens
        return mod.RunOutcome(**kw)
    return stub


def _solve(mod, repo):
    return mod.solve(repo, "fix the bug", model="m", api_base="b", api_key="k")


class CleanPatchCostsOneRun(unittest.TestCase):
    """A clean patch must not trigger a second model run."""

    def _run(self, agent_file, reason):
        mod = _load(agent_file)
        _neutralise(mod)
        mod._repair_reason = lambda *a, **k: reason
        calls = []
        mod._run_loop = _counting_run_loop(mod, calls)
        with tempfile.TemporaryDirectory() as repo:
            _solve(mod, repo)
        return len(calls)

    def test_ks43_clean_patch_runs_loop_once(self):
        self.assertEqual(self._run(_KS43, None), 1)

    def test_ks42_clean_patch_runs_loop_twice(self):
        """The regression KS43 fixes. If this ever returns 1, KS42 changed."""
        self.assertEqual(self._run(_KS42, None), 2)

    def test_ks43_still_repairs_a_broken_patch(self):
        """Removing polish must not disable repair on real defects."""
        reason = ("syntax", "the edited files contain syntax errors")
        self.assertEqual(self._run(_KS43, reason), 2)

    def test_ks43_repairs_on_every_objective_defect(self):
        for kind in ("test_fail", "no_test", "coverage", "syntax", "quality"):
            with self.subTest(kind=kind):
                self.assertEqual(self._run(_KS43, (kind, "because")), 2)


class PolishIsGone(unittest.TestCase):
    def test_build_polish_task_removed(self):
        mod = _load(_KS43)
        self.assertFalse(hasattr(mod, "_build_polish_task"))

    def test_ks42_still_has_it(self):
        mod = _load(_KS42)
        self.assertTrue(hasattr(mod, "_build_polish_task"))


class TokenAccounting(unittest.TestCase):
    def test_tokens_sum_across_main_and_repair_subloop(self):
        mod = _load(_KS43)
        _neutralise(mod)
        mod._repair_reason = lambda *a, **k: ("syntax", "broken")
        calls = []
        mod._run_loop = _counting_run_loop(mod, calls, tokens=(100, 10))
        with tempfile.TemporaryDirectory() as repo:
            out = _solve(mod, repo)
        self.assertEqual(len(calls), 2, "expected main loop + repair sub-loop")
        # Both runs spent tokens; both must be counted, adopted or not.
        self.assertEqual(out["prompt_tokens"], 200)
        self.assertEqual(out["completion_tokens"], 20)
        self.assertEqual(out["total_tokens"], 220)
        self.assertIn("tokens 220", out["message"])

    def test_clean_patch_reports_only_the_one_run(self):
        mod = _load(_KS43)
        _neutralise(mod)
        mod._repair_reason = lambda *a, **k: None
        mod._run_loop = _counting_run_loop(mod, [], tokens=(100, 10))
        with tempfile.TemporaryDirectory() as repo:
            out = _solve(mod, repo)
        self.assertEqual(out["total_tokens"], 110)

    def test_crash_path_still_reports_token_keys(self):
        mod = _load(_KS43)
        _neutralise(mod)

        def boom(config, task):
            raise RuntimeError("model died")

        mod._run_loop = boom
        with tempfile.TemporaryDirectory() as repo:
            out = _solve(mod, repo)
        self.assertIn("crashed", out["message"])
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            self.assertIn(key, out, f"{key} missing on the crash path")
        self.assertEqual(out["total_tokens"], 0)


if __name__ == "__main__":
    unittest.main()
