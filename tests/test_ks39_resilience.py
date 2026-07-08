"""KS39 R6 resilience regression tests.

Locks in the two changes that recover the R6-class 0.00 (empty-patch-on-SIGKILL):
  1. Wall-clock budget = 270s fallback, reserve >= 30s (so solve() returns
     before the live 300s hard kill; the gate harness scores 0.00 on any
     TimeoutExpired -- there is no disk recovery).
  2. _execute_command runs in its own process group and SIGKILLs the group on
     timeout, so an orphan-spawning command cannot hold the pipe and hang the
     round tail past the wall.

Stdlib only, no network, deterministic. NOT part of the submitted agent bundle
(kept under tests/ so it never touches the submission scope guard or the
32-file limit). Run:  python3 -m unittest tests.test_ks39_resilience -v
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import tempfile
import time
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_FILE = os.environ.get(
    "AGENT_FILE",
    os.path.join(_REPO_ROOT, "agent_cl_gpt_KingSlayer38.py"),
)
_FORBIDDEN_BUDGET_RE = re.compile(r"return\s*\(?\s*(?:280|300|570)\.0")


def _load_agent():
    spec = importlib.util.spec_from_file_location("submitted_agent", _AGENT_FILE)
    module = importlib.util.module_from_spec(spec)
    sys.modules["submitted_agent"] = module  # dataclasses need the module registered
    spec.loader.exec_module(module)
    return module


class WallClockBudgetTests(unittest.TestCase):
    """Change 1: the budget rule (270 fallback, reserve >= 30, no forbidden values)."""

    def setUp(self):
        self.m = _load_agent()
        self._saved = os.environ.get(self.m._BUDGET_ENV_KEY)

    def tearDown(self):
        if self._saved is None:
            os.environ.pop(self.m._BUDGET_ENV_KEY, None)
        else:
            os.environ[self.m._BUDGET_ENV_KEY] = self._saved

    def test_live_fallback_is_270(self):
        # Live duels do NOT pass TAU_AGENT_TIMEOUT_SECONDS -> fallback runs.
        os.environ.pop(self.m._BUDGET_ENV_KEY, None)
        self.assertEqual(self.m._resolve_wall_clock(), 270.0)

    def test_tau_300_yields_270(self):
        os.environ[self.m._BUDGET_ENV_KEY] = "300"
        self.assertEqual(self.m._resolve_wall_clock(), 270.0)

    def test_reserve_at_least_30(self):
        self.assertGreaterEqual(self.m._WALL_CLOCK_RESERVE_SECONDS, 30.0)

    def test_budget_not_a_forbidden_value(self):
        # 280/300/570 are the values gate.sh hard-blocks.
        self.assertNotIn(self.m._FALLBACK_WALL_CLOCK, (280.0, 300.0, 570.0))

    def test_source_has_no_hidden_forbidden_budget(self):
        # Guards against re-hiding a bad budget (e.g. float(28*10)) that would
        # slip past gate.sh's `return (280|300|570).0` grep.
        with open(_AGENT_FILE, "r", encoding="utf-8") as fh:
            src = fh.read()
        self.assertIsNone(_FORBIDDEN_BUDGET_RE.search(src))
        self.assertNotIn("28 * 10", src)


class ExecuteCommandTests(unittest.TestCase):
    """Change 2: process-group command execution."""

    def setUp(self):
        self.m = _load_agent()

    def test_happy_path(self):
        r = self.m._execute_command("echo hello_ks39", cwd="/tmp", timeout=5)
        self.assertEqual(r["returncode"], 0)
        self.assertIn("hello_ks39", r["output"])

    def test_simple_timeout_returns_124(self):
        t = time.monotonic()
        r = self.m._execute_command("sleep 10", cwd="/tmp", timeout=1)
        elapsed = time.monotonic() - t
        self.assertEqual(r["returncode"], 124)
        self.assertLess(elapsed, 6.0, "timeout not enforced promptly")

    def test_orphan_grandchild_is_killed_with_the_group(self):
        # The R6 mechanism: a command backgrounds a grandchild that outlives the
        # shell and holds the pipe. Old subprocess.run hung; the group-kill must
        # reap it. If the orphan survived it would create the marker.
        with tempfile.TemporaryDirectory() as d:
            marker = os.path.join(d, "orphan_survived.txt")
            cmd = f"( sleep 30 && touch {marker!r} ) & echo spawned; sleep 30"
            t = time.monotonic()
            r = self.m._execute_command(cmd, cwd=d, timeout=2)
            elapsed = time.monotonic() - t
            self.assertEqual(r["returncode"], 124)
            self.assertLess(elapsed, 8.0, "command did not return promptly (orphan hang)")
            time.sleep(4)  # window in which a surviving orphan would fire
            self.assertFalse(
                os.path.exists(marker),
                "orphan grandchild survived the process-group kill",
            )


class ContractTests(unittest.TestCase):
    """solve() still satisfies the validator entry-point contract."""

    def test_solve_signature(self):
        import inspect

        m = _load_agent()
        params = list(inspect.signature(m.solve).parameters)[:5]
        self.assertEqual(params, ["repo_path", "issue", "model", "api_base", "api_key"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
