"""Command line: python3 -m tokenfrugal run --repo DIR --task "..." """
import argparse
import json
import os
import sys

from .agent import Agent
from .audit import AuditLog
from .budget import Budget
from .policy import Policy
from .providers import OpenAICompatProvider, ScriptedProvider
from .tools import ToolBox


def build_parser():
    p = argparse.ArgumentParser(prog="tokenfrugal",
                                description="fix a repo under a token budget")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="fix a repo under a token budget")
    r.add_argument("--repo", required=True)
    r.add_argument("--task", required=True)
    r.add_argument("--budget", type=int, default=20000)
    r.add_argument("--provider", default="scripted", choices=["scripted", "openai"])
    r.add_argument("--model", default=None)
    r.add_argument("--audit", default="audit.jsonl")
    r.add_argument("--max-steps", type=int, default=12)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.cmd != "run":
        return 2
    audit = AuditLog(args.audit)
    policy = Policy(args.repo)
    toolbox = ToolBox(policy, audit)
    budget = Budget(args.budget)
    if args.provider == "openai":
        provider = OpenAICompatProvider(model=args.model)
    else:
        provider = ScriptedProvider([])
    agent = Agent(provider, toolbox, budget, audit, args.repo, max_steps=args.max_steps)
    out = agent.run(args.task)
    print(json.dumps(out, indent=2))
    return 0 if out.get("done") else 1


if __name__ == "__main__":
    sys.exit(main())
