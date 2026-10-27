# AGENTS.md: rules for coding agents working on ClinicVoice

## Read first
- docs/SPEC.md is the source of truth. docs/DECISIONS.md records choices.
- Work one phase at a time and wait for approval between phases.

## Code style
- Python 3.12. Add `from __future__ import annotations` to every module. Type hints everywhere. Pydantic v2 for validation. Use `logging.getLogger("clinicvoice")`; never `print()` outside CLI scripts.
- Never block the event loop. Wrap synchronous I/O in `asyncio.to_thread()`. All agent tools are async.
- TypeScript strict mode in the web app.
- Imports: standard library, third party, local, separated by blank lines.

## Security conventions
- Validate any externally supplied string used in a file path against `^[a-zA-Z0-9_-]+$`. Never build paths from raw input.
- Tools return generic, safe messages to the language model. Log full errors on the server only. Never expose stack traces, paths or internals.
- Use `yaml.safe_load` only. Use `encoding="utf-8"` for files.
- Secrets are never committed, echoed or logged. Only `.env.example` is committed.
- Never log full transcripts, phone numbers or patient details in technical logs.
- Every clinic-owned query must be tenant-scoped; PostgreSQL row-level security must stay enabled.

## Testing
- Run the full test suite before every commit. Do not commit failing tests.
- Every new module gets tests. Every bug found in a real call gets a regression test or eval.
- Warning and log paths are asserted in tests.

## Git
- Conventional Commits: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`.
- CI must pass before merging. Never bypass hooks.

## Documentation
- When code changes, update `docs/ARCHITECTURE.md`, `docs/CHANGELOG.md` and `docs/DECISIONS.md` as needed, in the same commit.

## SDK-sensitive code
- LiveKit Agents, the Sarvam plugin and provider SDKs change often. Check current official docs, pin versions, and isolate SDK-specific code behind our provider interfaces. Re-verify after any upgrade.

## Product guardrails
- No medical advice. No invented prices or availability. Escalate emergencies. Ask for recording consent. State that the caller is speaking to an AI assistant.
- The backend validates everything; the language model is never trusted.
