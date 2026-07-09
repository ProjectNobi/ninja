"""Reroll orchestrator path tests — executes the code, does not grep it.

Why this file exists: a `sys.executable` reference with no `import sys` once shipped
on this branch. py_compile passed, the forbidden-param grep passed, the whole
checklist was green -- and `_run_best_of_two_ks41` raised NameError the moment the
reroll fired. solve()'s `except Exception` then re-ran the full agent loop on a
tree attempt #1 had already dirtied, blowing the 300s wall and scoring 0.000 on
every round the reroll triggered. Compiling a function is not running it.

Every test below drives `_run_best_of_two_ks41` end to end on a real temp git repo
with `_run_loop` stubbed, then asserts the trace's `landed` field agrees with the
patch the function actually returned. A trace that disagrees with reality is worse
than no trace: it silently corrupts the fire/adopt rates the gate run exists to
measure.

Stdlib only, no network, deterministic. Kept under tests/ so it never enters the
submission bundle. Run:  python3 -m unittest tests.test_reroll_paths -v
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_FILE = os.environ.get(
    "AGENT_FILE",
    os.path.join(_REPO_ROOT, "agent_cl_gpt_KingSlayer41.py"),
)

# An issue naming foo.py and the symbol `compute`, so named_files/named_syms are
# both non-empty and multi_req is True.
_ISSUE = "Fix the bug in foo.py, the helper f and symbol `compute` are wrong. Also see qux.py"

# Trivial (one substantive line), touches no named target -> weak by king's rules.
_WEAK = {"bar.py": "def g():\n    return 3\n"}
# Substantive, touches the named file -> not weak.
_STRONG = {"foo.py": "def f():\n    a = 1\n    b = 2\n    return a + b\n"}


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True)


def _load_agent(trace_path=None):
    """Load the agent the way the validator harness does: exec into a bare module.

    _KS41_TRACE_PATH is read at import, so KS41_TRACE must be set before this runs.
    """
    if trace_path is None:
        os.environ.pop("KS41_TRACE", None)
    else:
        os.environ["KS41_TRACE"] = trace_path
    name = f"ks41_{len(sys.modules)}"
    spec = importlib.util.spec_from_file_location(name, _AGENT_FILE)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestNoUndefinedNames(unittest.TestCase):
    """The static half of the NameError guard: py_compile cannot see these."""

    def test_every_module_attribute_used_is_imported(self):
        """A `sys.executable` with no `import sys` compiles fine and dies at runtime.

        Symptom that motivated this test: the reroll raised NameError on its first
        real invocation, solve() fell back to a second full agent loop, and the
        round timed out to 0.000.
        """
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
        missing = sorted((used & stdlib) - imported)
        self.assertEqual(missing, [], f"used but never imported: {missing}")


class TestKeyAndBudget(unittest.TestCase):
    def setUp(self):
        self.mod = _load_agent()

    def test_key_is_the_kings_five_tuple(self):
        """_key_ks41 ranks by structure only. Any extra field is a deliberate
        divergence from the king and must be argued for, not slipped in."""
        info = self.mod._PatchInfoKS41(True, True, True, 2, False)
        key = self.mod._key_ks41(info)
        self.assertEqual(len(key), 5)
        self.assertEqual(key, (1, 1, 1, 2, 1))

    def test_wall_budget_leaves_a_return_path(self):
        """300s SIGKILL minus a 30s reserve. 280.0 is what the duel-7241 forensics
        blamed for empty-patch timeouts; keep the effective value checkable."""
        self.assertLessEqual(self.mod._resolve_wall_clock(), 270.0)
        self.assertGreaterEqual(self.mod._WALL_CLOCK_RESERVE_SECONDS, 30.0)

    def test_trace_disabled_is_a_noop(self):
        """An unset KS41_TRACE must not raise inside a scoring round."""
        self.mod._trace_ks41(event="x", why="y")


class _RerollHarness(unittest.TestCase):
    """Drives _run_best_of_two_ks41 against a real repo with _run_loop stubbed."""

    def setUp(self):
        self.trace = os.path.join(tempfile.mkdtemp(), "trace.jsonl")
        self.mod = _load_agent(self.trace)

    def _repo(self, dirty=False):
        d = tempfile.mkdtemp(prefix="ks41_test_")
        _git(d, "init", "-q")
        _git(d, "config", "user.email", "t@t")
        _git(d, "config", "user.name", "t")
        with open(os.path.join(d, "foo.py"), "w") as fh:
            fh.write("def f():\n    return 1\n")
        with open(os.path.join(d, "bar.py"), "w") as fh:
            fh.write("def g():\n    return 2\n")
        _git(d, "add", "-A")
        _git(d, "commit", "-qm", "base")
        if dirty:
            with open(os.path.join(d, "foo.py"), "a") as fh:
                fh.write("# uncommitted\n")
        return d

    def _run(self, a_writes, b_writes, dirty=False, b_raises=False,
             break_materialize=False, wall=270.0):
        repo = self._repo(dirty=dirty)
        calls = {"n": 0}

        def fake_run_loop(config, task):
            calls["n"] += 1
            if calls["n"] == 2 and b_raises:
                raise RuntimeError("attempt #2 exploded")
            writes = a_writes if calls["n"] == 1 else b_writes
            for path, content in writes.items():
                with open(os.path.join(config.repo_dir, path), "w") as fh:
                    fh.write(content)
            return self.mod.RunOutcome(
                success=True, patch=self.mod._collect_repo_patch(config.repo_dir),
                logs="", steps=1, cost=0.0, message="")

        self.mod._run_loop = fake_run_loop
        if break_materialize:
            self.mod._materialize_ks41 = lambda repo, sha, patch: False

        cfg = self.mod.RunConfig(repo_dir=repo, model_name="m", base_url="b",
                                 auth_token="t", wall_clock_limit=wall)
        outcome = self.mod._run_best_of_two_ks41(cfg, "task", _ISSUE)
        events = []
        if os.path.exists(self.trace):
            with open(self.trace) as fh:
                events = [json.loads(line) for line in fh]
        touched = sorted(self.mod._touched_paths_ks41(outcome.patch or ""))
        return outcome, events, touched, calls["n"]

    def _last(self, events, **match):
        for e in reversed(events):
            if all(e.get(k) == v for k, v in match.items()):
                return e
        self.fail(f"no trace event matching {match} in {events}")


class TestRerollExitPaths(_RerollHarness):
    def test_weak_attempt1_rerolls_and_adopts_better_attempt2(self):
        outcome, events, touched, loops = self._run(_WEAK, _STRONG)
        self.assertEqual(loops, 2, "reroll should have fired on a weak attempt #1")
        ev = self._last(events, event="attempt2")
        self.assertEqual(ev["why"], "adopted")
        self.assertEqual(ev["landed"], "attempt2")
        # The trace claims #2 landed; the returned patch must actually be #2's.
        self.assertEqual(touched, ["foo.py"])

    def test_strong_attempt1_does_not_reroll(self):
        outcome, events, touched, loops = self._run(_STRONG, _WEAK)
        self.assertEqual(loops, 1, "a strong attempt #1 must not pay for a second draw")
        ev = self._last(events, event="no_reroll")
        self.assertEqual(ev["why"], "not_weak")
        self.assertEqual(touched, ["foo.py"])

    def test_materialize_failure_restores_attempt1_and_says_so(self):
        """The bug this pins: the trace once logged adopted=True at the key
        comparison, before the swap could still fail. Fire/adopt rates were
        overcounted for every round that reached this branch."""
        outcome, events, touched, loops = self._run(_WEAK, _STRONG, break_materialize=True)
        self.assertEqual(loops, 2)
        ev = self._last(events, event="attempt2")
        self.assertEqual(ev["why"], "materialize_b_failed")
        self.assertEqual(ev["landed"], "attempt1")
        self.assertEqual(touched, ["bar.py"], "attempt #1's patch must be what returns")

    def test_attempt2_exception_falls_open_to_attempt1(self):
        outcome, events, touched, loops = self._run(_WEAK, _STRONG, b_raises=True)
        ev = self._last(events, event="bail")
        self.assertEqual(ev["why"], "run_loop_b_exception")
        self.assertEqual(touched, ["bar.py"])

    def test_dirty_tree_never_rerolls(self):
        """A reroll resets the tree. If the tree was dirty before attempt #1, the
        reset would destroy work that was never ours to destroy."""
        outcome, events, touched, loops = self._run(_WEAK, _STRONG, dirty=True)
        self.assertEqual(loops, 1)
        ev = self._last(events, event="bail")
        self.assertEqual(ev["why"], "not_clean_start")

    def test_insufficient_budget_never_rerolls(self):
        """Attempt #2 needs >=160s. Firing with less is how a round overruns the
        300s wall and returns an empty patch."""
        outcome, events, touched, loops = self._run(_WEAK, _STRONG, wall=100.0)
        self.assertEqual(loops, 1)
        ev = self._last(events, event="no_reroll")
        self.assertEqual(ev["why"], "insufficient_budget")


class TestTraceCompleteness(_RerollHarness):
    def test_every_event_carries_remaining(self):
        """Without wall time at the exit, a timed-out round is indistinguishable
        from a crashed one, and the trace cannot speak to timeout hypotheses."""
        _, events, _, _ = self._run(_WEAK, _STRONG)
        for ev in events:
            self.assertIn("remaining", ev, f"event without remaining: {ev}")

    def test_trace_landed_matches_returned_patch(self):
        """The invariant the whole trace rests on, asserted across both outcomes."""
        for name, a, b, kwargs, expect_file in [
            ("adopted", _WEAK, _STRONG, {}, "foo.py"),
            ("restored", _WEAK, _STRONG, {"break_materialize": True}, "bar.py"),
        ]:
            with self.subTest(case=name):
                self.setUp()
                _, events, touched, _ = self._run(a, b, **kwargs)
                ev = self._last(events, event="attempt2")
                landed_2 = ev["landed"] == "attempt2"
                self.assertEqual(touched, [expect_file])
                self.assertEqual(landed_2, expect_file == "foo.py")


if __name__ == "__main__":
    unittest.main(verbosity=2)
