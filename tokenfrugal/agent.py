"""The loop: a compact repo map, one tool call at a time, trimmed observations."""
import json

from .budget import BudgetExceeded
from .policy import PolicyError
from .repo import RepoMap
from .tokens import count_messages

SYSTEM = 'You are a coding agent. Reply with ONE JSON object containing thought, tool, args. The tool field must be exactly one of: read_file, search, write_file, run_tests, done. Never put arguments or braces inside the tool name. Put arguments only in args.\nExamples of valid JSON actions:\n{"thought":"inspect code","tool":"read_file","args":{"path":"inventory/total.py"}}\n{"thought":"find code","tool":"search","args":{"pattern":"line_value","glob":"*.py"}}\n{"thought":"edit code","tool":"write_file","args":{"path":"example.py","content":"complete replacement file contents"}}\n{"thought":"verify","tool":"run_tests","args":{"cmd":"python3 -m unittest discover -s tests -q"}}\n{"thought":"finish","tool":"done","args":{"summary":"what changed and test results"}}\nRead relevant code before editing. Change as little as possible. Do not edit tests. Run tests successfully before done. Keep thought short.'

OBS_LIMIT = 1200


def trim(text, limit=OBS_LIMIT):
    """Observations are trimmed before they go back into the context."""
    text = text if isinstance(text, str) else str(text)
    return text if len(text) <= limit else text[:limit] + "\n[trimmed]"


class Agent:
    def __init__(self, provider, toolbox, budget, audit, root, max_steps=12):
        self.provider = provider
        self.toolbox = toolbox
        self.budget = budget
        self.audit = audit
        self.root = root
        self.max_steps = max_steps
        self.transcript = []
        self.tests_passed = False
        self.read_cache = {}

    def run(self, task):
        repo_map = RepoMap(self.root).render()
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": "Repo map:\n%s\n\nTask: %s" % (repo_map, task)},
        ]
        self.audit.write("start", task=task, provider=self.provider.name,
                         prompt_tokens=count_messages(messages))
        for _ in range(self.max_steps):
            try:
                self.budget.check(count_messages(messages) + 512)
            except BudgetExceeded as exc:
                return {"done": False, "stop": "budget", "detail": str(exc), "spent": self.budget.spent}
            try:
                action = self.provider.act(messages, max_tokens=512)
            except (ValueError, RuntimeError) as exc:
                self.audit.write("stop", reason="provider_error", detail=str(exc))
                return {"done": False, "stop": "provider_error", "detail": str(exc)}
            used = self.provider.usage(messages, action)
            try:
                self.budget.check(used)
            except BudgetExceeded as exc:
                self.budget.charge(used)
                self.audit.write("stop", reason="budget", detail=str(exc))
                return {"done": False, "stop": "budget", "detail": str(exc),
                        "spent": self.budget.spent, "steps": len(self.transcript)}
            self.budget.charge(used)
            self.audit.write("model", step=len(self.transcript) + 1, tokens=used,
                             tool=action.get("tool"),
                             thought=(action.get("thought") or "")[:200])

            tool = action.get("tool")
            if tool == "done":
                if not self.tests_passed:
                    self.audit.write("stop", reason="unverified_done")
                    return {"done": False, "stop": "unverified_done", "spent": self.budget.spent}
                summary = (action.get("args") or {}).get("summary", "")
                self.audit.write("done", summary=summary, spent=self.budget.spent)
                return {"done": True, "summary": summary, "spent": self.budget.spent,
                        "calls": self.budget.calls, "steps": len(self.transcript)}
            if tool in ("write_file", "run_tests"):
                self.tests_passed = False
            try:
                key = json.dumps([tool, action.get("args")], sort_keys=True)
                if tool in ("read_file", "search") and key in self.read_cache:
                    observation = "Already inspected this exact request. Use its earlier observation. Inspect a different relevant file, then write the corrected implementation and run tests."
                else:
                    observation = self.toolbox.call(tool, action.get("args"))
                    if tool in ("read_file", "search"):
                        self.read_cache[key] = True
                if tool == "write_file":
                    self.read_cache.clear()
                if tool == "write_file":
                    self.tests_passed = False
                elif tool == "run_tests":
                    self.tests_passed = observation.startswith("exit 0\n")
            except (PolicyError, OSError, TypeError, ValueError) as exc:
                observation = "error: %s" % exc
            self.transcript.append({"tool": tool, "args": action.get("args"),
                                    "observation": trim(observation)})
            messages.append({"role": "assistant", "content": json.dumps(action)})
            messages.append({"role": "user", "content": "observation:\n" + trim(observation)})
        self.audit.write("stop", reason="max_steps")
        return {"done": False, "stop": "max_steps", "spent": self.budget.spent,
                "steps": len(self.transcript)}
