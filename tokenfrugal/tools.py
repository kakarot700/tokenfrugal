"""The agent's tools. Every observation is trimmed, because observations are
what usually blow a context budget."""
import os
import subprocess

from .policy import PolicyError

MAX_READ_LINES = 120
MAX_SEARCH_HITS = 40
MAX_TEST_CHARS = 900


class ToolBox:
    def __init__(self, policy, audit):
        self.policy = policy
        self.audit = audit

    # --- tools -----------------------------------------------------------
    def read_file(self, path, start=1, end=None):
        full = self.policy.resolve(path)
        with open(full, errors="ignore") as fh:
            lines = fh.read().splitlines()
        start = max(1, int(start))
        end = int(end) if end else start + MAX_READ_LINES - 1
        end = min(end, start + MAX_READ_LINES - 1, len(lines))
        body = "\n".join("%4d| %s" % (n, lines[n - 1]) for n in range(start, end + 1))
        note = "" if end >= len(lines) else "\n[truncated at line %d of %d]" % (end, len(lines))
        return body + note

    def search(self, pattern, glob=None):
        import re
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            return "bad pattern: %s" % exc
        hits = []
        for rel in self._files():
            if glob and not rel.endswith(glob.lstrip("*")):
                continue
            try:
                with open(os.path.join(self.policy.root, rel), errors="ignore") as fh:
                    for n, line in enumerate(fh, 1):
                        if rx.search(line):
                            hits.append("%s:%d: %s" % (rel, n, line.strip()[:160]))
                            if len(hits) >= MAX_SEARCH_HITS:
                                return "\n".join(hits) + "\n[more hits not shown]"
            except OSError:
                continue
        return "\n".join(hits) if hits else "no matches"

    def write_file(self, path, content):
        full = self.policy.check_write(path)
        os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
        with open(full, "w") as fh:
            fh.write(content)
        return "wrote %s (%d bytes, %d lines)" % (
            path, len(content.encode()), content.count("\n") + 1)

    def run_tests(self, cmd="python3 -m unittest discover -q"):
        import shlex
        argv = shlex.split(cmd)
        allowed = (["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
                   ["python3", "-m", "unittest", "discover", "-q"])
        if argv not in allowed:
            raise PolicyError("only fixed unittest discovery commands are allowed")
        proc = subprocess.run(argv, shell=False, cwd=self.policy.root,
                              capture_output=True, text=True, timeout=120)
        out = (proc.stdout + proc.stderr).strip()
        if len(out) > MAX_TEST_CHARS:
            out = out[:MAX_TEST_CHARS] + "\n[output trimmed]"
        return "exit %d\n%s" % (proc.returncode, out or "(no output)")

    # --- dispatch --------------------------------------------------------
    def call(self, name, args):
        self.policy.check_tool(name)
        fn = getattr(self, name, None)
        if fn is None:
            raise PolicyError("unknown tool: %r" % name)
        args = args or {}
        result = fn(**args)
        self.audit.write("tool", tool=name, args=args, result_chars=len(result))
        return result

    def _files(self):
        from .repo import RepoMap
        return RepoMap(self.policy.root).files()
