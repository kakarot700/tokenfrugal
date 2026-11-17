# TokenFrugal

Prototype coding-agent harness for Geek Room x HackCulture Global AI Hackathon 2026.
Track: Build a Coding Agent That Gets the Job Done on the Fewest Tokens.
Entrant: Shubham Yadav. Built and submitted by Ira with disclosed AI delegation,
as permitted in the organizer's written response. No minimum-token result is claimed.

## Run without payment or API credentials

Requires Python 3.10+. No dependencies for the offline demo or tests.

```sh
python3 -m unittest discover -s tests -v
python3 demo/run_demo.py
python3 -m tokenfrugal --help
```

The demo fixes a small inventory example using a deterministic scripted plan.
It is NOT a live language-model run. Tools execute and tests actually run.
Reported token counts are estimates, not provider-billed usage or proven savings.
The optional OpenAI-compatible API adapter has not been live-provider validated.
Use the CLI help for its available flags; no paid API key is bundled or required.

## Implemented

- Compact repository map, selective line reads and bounded search results.
- Trimmed observations and a maximum-step stop.
- Estimated prompt-plus-512-output-token preflight budget check.
- API output-token cap, usage accounting and audit records.
- Relative-path checks, symlink-escape refusal and write allowlists.
- Fixed unittest-discovery subprocess argument lists, no shell expansion.
- A done action is rejected unless tests passed since the latest write.
- Malformed provider actions and exhausted scripts are failures, not success.

## Not implemented or established

Provider failover, per-user dollar caps, confidential-repository routing, arbitrary
shell/git approvals, Bifrost deployment, and a live token-savings baseline are not
implemented or demonstrated. Bifrost can only be considered an optional compatible
endpoint. No public GitHub repository or platform acceptance is claimed here.

Token estimation may differ from actual billing. Preflight checks are not a hard
monetary cap; providers must enforce their own spend limits. The toolbox is NOT an
OS sandbox. Tests run repository code with the current process's permissions. Use
only a disposable container/VM without secrets for untrusted repositories.

## Submission and AI disclosure

See AI_USE.md and VALIDATION_NOTES.md. This revised archive supersedes the earlier
archive and any conflicting claims in its pitch deck. Source is MIT licensed.
The entrant retains his rights under the event's terms; no third-party service
credentials or private data are included.

## Actual live-model validation (16 November 2026)
A free local Qwen2.5-Coder-1.5B run repaired the small inventory fixture using 7 calls / 4,931 actual reported tokens. Both unchanged fixture tests passed independently. See docs/live-validation for complete evidence and limitations. This is a single development fixture, not a claim of general success or superiority. The original offline scripted demonstration remains labelled separately.

## Live run on NVIDIA NIM (17 Nov 2026)

`demo/live-validation/nemotron-ultra-live-audit.jsonl` is the audit trail of a real run
against NVIDIA's own hosted model `nvidia/nemotron-3-ultra-550b-a55b` through the
OpenAI-compatible NIM endpoint. The agent fixed the failing fixture on its own in 5 model
calls / 3,623 tokens, and the repo's tests passed afterwards. No paid credits were used.

Reasoning models spend part of the reply budget thinking, so `providers.py` now asks for at
least 2048 reply tokens and falls back to `reasoning_content` when `content` carries no JSON.
