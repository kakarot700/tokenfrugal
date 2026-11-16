"""Append-only JSONL audit trail: every model call, tool call and result."""
import json
import os
import time


class AuditLog:
    def __init__(self, path):
        self.path = path
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        open(self.path, "a").close()

    def write(self, kind, **fields):
        row = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "kind": kind}
        row.update(fields)
        with open(self.path, "a") as fh:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
        return row

    def rows(self):
        with open(self.path) as fh:
            return [json.loads(line) for line in fh if line.strip()]
