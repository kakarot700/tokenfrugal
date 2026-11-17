"""Model providers.

ScriptedProvider is a deterministic stand-in so the demo and the tests run
with no API key and no network. It is not a language model: it replays a plan.
OpenAICompatProvider talks to any OpenAI-compatible /chat/completions endpoint.
"""
import json
import os
import urllib.request

from .tokens import count, count_messages


class ScriptedProvider:
    """Replays a fixed plan. Used for the offline demo and the tests."""

    name = "scripted"

    def __init__(self, steps):
        self.steps = list(steps)
        self.i = 0

    def act(self, messages, max_tokens=512):
        if self.i >= len(self.steps):
            raise RuntimeError("script exhausted without verified completion")
        step = self.steps[self.i]
        self.i += 1
        return dict(step)

    def usage(self, messages, reply):
        return count_messages(messages) + count(json.dumps(reply))


class OpenAICompatProvider:
    """Any OpenAI-compatible endpoint: OPENAI_BASE_URL, OPENAI_API_KEY, OPENAI_MODEL."""

    name = "openai"

    def __init__(self, model=None, base_url=None, api_key=None, timeout=60):
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL",
                          "https://api.openai.com/v1")).rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.timeout = timeout
        self.last_usage = 0

    def act(self, messages, max_tokens=512):
        if not self.api_key:
            raise RuntimeError("set OPENAI_API_KEY (or use --provider scripted)")
        # reasoning models (e.g. NVIDIA Nemotron) spend part of max_tokens thinking
        cap = max(max_tokens, int(os.environ.get("TOKENFRUGAL_MIN_REPLY_TOKENS", "2048")))
        body = json.dumps({"model": self.model, "messages": messages,
                           "temperature": 0, "max_tokens": cap}).encode()
        req = urllib.request.Request(
            self.base_url + "/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode())
        msg = data["choices"][0]["message"]
        text = msg.get("content") or ""
        if "{" not in text:
            text = text + (msg.get("reasoning_content") or msg.get("reasoning") or "")
        self.last_usage = (data.get("usage") or {}).get("total_tokens") or 0
        return _parse_action(text)

    def usage(self, messages, reply):
        return self.last_usage or (count_messages(messages) + count(json.dumps(reply)))


def _parse_action(text):
    """Pull one JSON object out of a model reply."""
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break
                    if "tool" in obj:
                        return {"thought": obj.get("thought", ""),
                                "tool": obj["tool"], "args": obj.get("args") or {}}
                    break
        start = text.find("{", start + 1)
    raise ValueError("no valid tool action in provider reply")
