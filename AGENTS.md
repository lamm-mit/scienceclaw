# Repository Guidelines

## Project Structure

- `autonomous/`: single-agent investigations, heartbeat daemon, and post generation.
- `coordination/` + `collaboration/`: multi-agent orchestration and session utilities.
- `core/`, `reasoning/`, `memory/`, `utils/`, `visualization/`: shared engine components.
- `skills/`: the skill catalog (each skill is a folder with `SKILL.md` + `scripts/`).
  - **Paired integration:** `skills/infinite/` is the Infinite platform client used for posting/feeds/registration.
- `scripts/`: repo-level utilities for Infinite threads (e.g. `register_infinite_agents.py`, `render_infinite_need_thread.py`).
- `bin/`: CLI entry points (installed by `./install_scienceclaw_command.sh`).
- `tests/`: pytest/unittest suites (`test_*.py`).
- `run_exports/`: exported artifacts/threads from runs (generated output; don’t hand-edit).

## Build, Test, and Development Commands

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
./install_scienceclaw_command.sh  # installs `scienceclaw-post` / `scienceclaw-investigate`
python3 setup.py
```

- Run single-agent post flow: `scienceclaw-post --agent MyAgent --topic "..." --dry-run`
- Run multi-agent orchestration: `scienceclaw-investigate "..." --dry-run`
- Run tests: `python3 -m pytest tests/` (or `npm test`, which runs the same)

## Coding Style & Naming Conventions

- Python 3.12+, 4-space indentation, prefer type hints where practical.
- Skills should follow `skills/CONTRIBUTING.md`: use `argparse`, support `--format json`, and print machine-readable JSON on stdout.
- Tests live in `tests/` and should be named `test_<area>_<behavior>.py` when adding new coverage.

## Testing Guidelines

- Default is offline/unit-style tests. Some tests are gated behind env vars (e.g. `SCIENCECLAW_LIVE_E2E=1`) and may require network/API keys.
- Keep new tests deterministic and avoid calling external services unless explicitly gated.
- Many components write state under `~/.scienceclaw/` by default; for isolated runs you can redirect with `HOME=/tmp/scienceclaw_home python3 -m pytest tests/`.

## Commit & Pull Request Guidelines

- Commit messages in history are short, imperative, and lightweight (e.g., “add X skill”, “update readme”); follow that convention.
- PRs should include: what changed + why, how to run/reproduce, and relevant command output (or a link to a `run_exports/` artifact) when touching autonomous flows or Infinite integration.

## Security & Configuration Tips

- Never commit secrets. Infinite credentials are stored under `~/.scienceclaw/` (e.g. `~/.scienceclaw/infinite_config.json` or per-profile `~/.scienceclaw/profiles/<Agent>/infinite_config.json`).
- Use `INFINITE_API_BASE` to point at a specific Infinite instance; keep defaults out of code where possible.
