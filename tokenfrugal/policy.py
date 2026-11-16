"""What the agent may touch.

Every path is resolved and must stay inside the repo root. Writes outside the
allowlist need an approval callback; the default callback refuses.
"""
import os


class PolicyError(PermissionError):
    pass


class Policy:
    def __init__(self, root, allowed_tools=None, write_allow=None, approve=None):
        self.root = os.path.realpath(root)
        self.allowed_tools = set(allowed_tools or
                                 ["read_file", "search", "write_file", "run_tests", "done"])
        self.write_allow = list(write_allow or [])
        self.approve = approve or (lambda action, detail: False)

    def resolve(self, path):
        """A path inside the root, or PolicyError."""
        if not path or path.startswith("/") or ".." in path.split("/"):
            raise PolicyError("path must be relative and inside the repo: %r" % path)
        full = os.path.realpath(os.path.join(self.root, path))
        if full != self.root and not full.startswith(self.root + os.sep):
            raise PolicyError("path escapes the repo: %r" % path)
        return full

    def check_tool(self, name):
        if name not in self.allowed_tools:
            raise PolicyError("tool not allowed: %r" % name)

    def check_write(self, path):
        full = self.resolve(path)
        if not self.write_allow:
            return full
        rel = os.path.relpath(full, self.root)
        if any(rel == p or rel.startswith(p.rstrip("/") + "/") for p in self.write_allow):
            return full
        if self.approve("write_file", rel):
            return full
        raise PolicyError("write outside the allowlist was not approved: %r" % rel)
