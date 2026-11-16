"""Token accounting.

Uses tiktoken when it happens to be installed; otherwise a stable estimate
(about 4 characters per token). Every number the agent reports comes from
this one function, so the benchmark and the budget agree.
"""
from functools import lru_cache


@lru_cache(maxsize=1)
def _encoder():
    try:
        import tiktoken  # optional
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


def count(text):
    """Tokens in a string."""
    if not text:
        return 0
    enc = _encoder()
    if enc is not None:
        return len(enc.encode(text))
    return max(1, (len(text) + 3) // 4)


def count_messages(messages):
    """Tokens in a chat-style message list, plus a small per-message overhead."""
    total = 0
    for m in messages:
        total += count(m.get("role", "")) + count(m.get("content", "")) + 4
    return total
