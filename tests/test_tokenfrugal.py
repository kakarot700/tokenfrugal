import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tokenfrugal.agent import Agent, trim
from tokenfrugal.audit import AuditLog
from tokenfrugal.budget import Budget, BudgetExceeded
from tokenfrugal.policy import Policy, PolicyError
from tokenfrugal.providers import ScriptedProvider, _parse_action
from tokenfrugal.repo import RepoMap
from tokenfrugal.tokens import count, count_messages
from tokenfrugal.tools import ToolBox

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(os.path.dirname(HERE), "demo", "sample_repo")


class BudgetTest(unittest.TestCase):
    def test_charge_and_left(self):
        b = Budget(100)
        b.charge(30)
        self.assertEqual(b.left, 70)
        self.assertEqual(b.calls, 1)

    def test_refuses_before_charging(self):
        b = Budget(50)
        b.charge(40)
        with self.assertRaises(BudgetExceeded):
            b.check(20)
        self.assertEqual(b.spent, 40)

    def test_rejects_zero(self):
        with self.assertRaises(ValueError):
            Budget(0)


class PolicyTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.policy = Policy(self.root)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_absolute_path_refused(self):
        with self.assertRaises(PolicyError):
            self.policy.resolve("/etc/passwd")

    def test_parent_escape_refused(self):
        with self.assertRaises(PolicyError):
            self.policy.resolve("../outside.txt")

    def test_inside_ok(self):
        self.assertTrue(self.policy.resolve("a/b.txt").startswith(self.root))

    def test_tool_allowlist(self):
        with self.assertRaises(PolicyError):
            self.policy.check_tool("rm_rf")

    def test_write_allowlist_needs_approval(self):
        p = Policy(self.root, write_allow=["src"])
        p.check_write("src/x.py")
        with self.assertRaises(PolicyError):
            p.check_write("other/x.py")
        p2 = Policy(self.root, write_allow=["src"], approve=lambda a, d: True)
        p2.check_write("other/x.py")


class TokensTest(unittest.TestCase):
    def test_count_grows_with_text(self):
        self.assertGreater(count("hello world " * 20), count("hello"))

    def test_messages_overhead(self):
        msgs = [{"role": "user", "content": "hi"}]
        self.assertGreater(count_messages(msgs), count("hi"))


class RepoMapTest(unittest.TestCase):
    def test_map_lists_symbols_not_contents(self):
        text = RepoMap(SAMPLE).render()
        self.assertIn("inventory/total.py", text)
        self.assertIn("total_value", text)
        self.assertNotIn("sum(line_value", text)


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        shutil.copytree(SAMPLE, os.path.join(self.root, "repo"))
        self.repo = os.path.join(self.root, "repo")
        self.audit = AuditLog(os.path.join(self.root, "a.jsonl"))
        self.box = ToolBox(Policy(self.repo), self.audit)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_read_file_numbers_lines(self):
        out = self.box.call("read_file", {"path": "inventory/total.py"})
        self.assertIn("1|", out)

    def test_search_finds_symbol(self):
        out = self.box.call("search", {"pattern": "def total_value"})
        self.assertIn("inventory/total.py", out)

    def test_write_then_tests_pass(self):
        fixed = ('def line_value(item):\n    return item["price"] * item["qty"]\n\n\n'
                 'def total_value(items):\n    return sum(line_value(i) for i in items)\n')
        self.box.call("write_file", {"path": "inventory/total.py", "content": fixed})
        out = self.box.call("run_tests", {"cmd": "python3 -m unittest discover -s tests -q"})
        self.assertIn("exit 0", out)

    def test_audit_records_tool_calls(self):
        self.box.call("search", {"pattern": "price"})
        self.assertEqual(self.audit.rows()[-1]["tool"], "search")


class AgentTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        shutil.copytree(SAMPLE, os.path.join(self.root, "repo"))
        self.repo = os.path.join(self.root, "repo")
        self.audit = AuditLog(os.path.join(self.root, "a.jsonl"))

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _agent(self, steps, budget=5000):
        return Agent(ScriptedProvider(steps), ToolBox(Policy(self.repo), self.audit),
                     Budget(budget), self.audit, self.repo)

    def test_done_after_fix(self):
        fixed = 'def line_value(item):\n    return item["price"] * item["qty"]\ndef total_value(items):\n    return sum(line_value(i) for i in items)\n'
        steps = [
            {"tool": "read_file", "args": {"path": "inventory/total.py"}},
            {"tool": "write_file", "args": {"path": "inventory/total.py", "content": fixed}},
            {"tool": "run_tests", "args": {"cmd": "python3 -m unittest discover -s tests -q"}},
            {"tool": "done", "args": {"summary": "fixed"}},
        ]
        out = self._agent(steps).run("fix the tests")
        self.assertTrue(out["done"])
        self.assertGreater(out["spent"], 0)

    def test_budget_stops_the_run(self):
        steps = [{"tool": "read_file", "args": {"path": "inventory/total.py"}}] * 20
        out = self._agent(steps, budget=60).run("loop")
        self.assertFalse(out["done"])
        self.assertEqual(out["stop"], "budget")

    def test_bad_tool_is_an_observation_not_a_crash(self):
        steps = [{"tool": "nope", "args": {}}, {"tool": "done", "args": {}}]
        out = self._agent(steps).run("x")
        self.assertFalse(out["done"])

    def test_trim_shortens_long_observations(self):
        self.assertLess(len(trim("x" * 5000)), 1300)


class ParseTest(unittest.TestCase):
    def test_parses_json_in_prose(self):
        a = _parse_action('sure: {"thought": "t", "tool": "done", "args": {}} ok')
        self.assertEqual(a["tool"], "done")

    def test_unparseable_is_rejected(self):
        with self.assertRaises(ValueError):
            _parse_action("no json here")


if __name__ == "__main__":
    unittest.main()


class RegressionTest(AgentTest):
    def test_done_without_tests_is_not_success(self):
        out = self._agent([{"tool": "done", "args": {}}]).run("x")
        self.assertFalse(out["done"])
        self.assertEqual(out["stop"], "unverified_done")

    def test_budget_refusal_does_not_call_provider(self):
        a = self._agent([{"tool": "done", "args": {}}], budget=1)
        out = a.run("x")
        self.assertEqual(a.provider.i, 0)
        self.assertEqual(out["stop"], "budget")

    def test_shell_commands_rejected(self):
        box = self._agent([]).toolbox
        with self.assertRaises(PolicyError):
            box.call("run_tests", {"cmd": "touch should-not-exist"})

    def test_failed_tests_cannot_finish(self):
        out = self._agent([
            {"tool": "run_tests", "args": {"cmd": "python3 -m unittest discover -s tests -q"}},
            {"tool": "done", "args": {}}]).run("x")
        self.assertFalse(out["done"])
