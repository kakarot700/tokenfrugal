"""A compact map of the repo, so the model never needs the whole tree.

Instead of pasting every file, the agent gets one line per file: its path, its
size, and the names it defines. It then reads only the lines it needs.
"""
import os
import re

SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
             ".pytest_cache", ".mypy_cache", "dist", "build", ".idea"}
TEXT_EXT = {".py", ".md", ".txt", ".toml", ".cfg", ".ini", ".json", ".yml",
            ".yaml", ".js", ".ts", ".html", ".css", ".sh"}
MAX_BYTES = 200_000

_DEF = re.compile(r"^\s*(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
_JS = re.compile(r"^\s*(?:function|class|const)\s+([A-Za-z_$][A-Za-z0-9_$]*)", re.M)


class RepoMap:
    def __init__(self, root):
        self.root = os.path.realpath(root)

    def files(self):
        out = []
        for base, dirs, names in os.walk(self.root):
            dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
            for name in sorted(names):
                ext = os.path.splitext(name)[1].lower()
                if ext not in TEXT_EXT:
                    continue
                full = os.path.join(base, name)
                try:
                    if os.path.getsize(full) > MAX_BYTES:
                        continue
                except OSError:
                    continue
                out.append(os.path.relpath(full, self.root))
        return out

    def symbols(self, rel):
        try:
            with open(os.path.join(self.root, rel), errors="ignore") as fh:
                text = fh.read()
        except OSError:
            return []
        found = _DEF.findall(text) if rel.endswith(".py") else _JS.findall(text)
        return found[:12]

    def lines(self, rel):
        try:
            with open(os.path.join(self.root, rel), errors="ignore") as fh:
                return sum(1 for _ in fh)
        except OSError:
            return 0

    def render(self, max_files=120):
        """One line per file. This is the whole context the agent starts with."""
        rows = []
        for rel in self.files()[:max_files]:
            syms = self.symbols(rel)
            tail = (" — " + ", ".join(syms)) if syms else ""
            rows.append("%s (%d lines)%s" % (rel, self.lines(rel), tail))
        return "\n".join(rows)

    def full_text(self):
        """Every file's contents, for the naive baseline only."""
        chunks = []
        for rel in self.files():
            try:
                with open(os.path.join(self.root, rel), errors="ignore") as fh:
                    chunks.append("### %s\n%s" % (rel, fh.read()))
            except OSError:
                continue
        return "\n\n".join(chunks)
