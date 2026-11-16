"""Offline demo: the agent fixes a real bug in demo/sample_repo.

No API key, no network: a scripted provider replays the plan a model would
produce, so the token accounting is real and the run is repeatable.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tokenfrugal.agent import Agent
from tokenfrugal.audit import AuditLog
from tokenfrugal.budget import Budget
from tokenfrugal.policy import Policy
from tokenfrugal.providers import ScriptedProvider
from tokenfrugal.tools import ToolBox

HERE = os.path.dirname(os.path.abspath(__file__))
FIXED = '''"""Stock valuation for a tiny shop."""


def line_value(item):
    return item["price"] * item["qty"]


def total_value(items):
    return sum(line_value(i) for i in items)
'''

STEPS = [
    {"thought": "read the failing module", "tool": "read_file",
     "args": {"path": "inventory/total.py"}},
    {"thought": "line_value ignores qty", "tool": "write_file",
     "args": {"path": "inventory/total.py", "content": FIXED}},
    {"thought": "check", "tool": "run_tests",
     "args": {"cmd": "python3 -m unittest discover -s tests -q"}},
    {"thought": "green", "tool": "done",
     "args": {"summary": "line_value now multiplies price by qty"}},
]


def main():
    work = tempfile.mkdtemp(prefix="tokenfrugal-demo-")
    repo = os.path.join(work, "repo")
    shutil.copytree(os.path.join(HERE, "sample_repo"), repo)
    audit = AuditLog(os.path.join(work, "audit.jsonl"))
    toolbox = ToolBox(Policy(repo), audit)
    budget = Budget(4000)
    agent = Agent(ScriptedProvider(STEPS), toolbox, budget, audit, repo)
    out = agent.run("the inventory tests fail: fix them")
    print("result:", out)
    print("audit rows:", len(audit.rows()))
    print("audit file:", audit.path)
    return 0 if out.get("done") else 1


if __name__ == "__main__":
    sys.exit(main())
