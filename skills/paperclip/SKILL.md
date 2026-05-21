---
name: paperclip
description: Onboard and manage Paperclip AI for research-paper knowledge and agent orchestration
metadata:
  openclaw:
    emoji: "📎"
    requires:
      bins:
        - python3
        - node
        - npm
        - npx
---

# Paperclip

Use Paperclip AI from ScienceClaw to onboard a local Paperclip instance, run health checks, and start the service that provides AI agents with indexed literature and orchestration capabilities.

Paperclip's quickstart command is:

```bash
npx paperclipai onboard --yes
```

## Usage

### Check local prerequisites

```bash
python3 {baseDir}/scripts/paperclip.py --action check --format json
```

### Show the onboarding command without running it

```bash
python3 {baseDir}/scripts/paperclip.py --action onboard --format json
```

### Run non-interactive onboarding

```bash
python3 {baseDir}/scripts/paperclip.py --action onboard --execute --yes --format json
```

By default this detaches the long-running Paperclip server and returns a PID plus a log file.

### Run Paperclip health checks

```bash
python3 {baseDir}/scripts/paperclip.py --action doctor --execute --format json
```

### Start Paperclip

```bash
python3 {baseDir}/scripts/paperclip.py --action run --execute --format json
```

## Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--action` | Operation: `check`, `onboard`, `doctor`, `run`, or `version` | `check` |
| `--execute` | Actually run the Paperclip command; omitted means dry run | false |
| `--detach` | Run long-lived `onboard`/`run` commands in the background | true for `onboard`/`run` |
| `--foreground` | Keep long-lived commands attached to the current process | false |
| `--yes` | Pass `--yes` to `paperclipai onboard` | true |
| `--run-after-onboard` | Pass `--run` to `paperclipai onboard` | false |
| `--repair` | Pass `--repair` to `paperclipai doctor` | false |
| `--bind` | Optional bind target for onboarding, such as `tailnet` | - |
| `--work-dir` | Directory where the Paperclip CLI runs | current directory |
| `--timeout` | Command timeout in seconds | 600 |
| `--wait-seconds` | Seconds to watch a detached command before returning | 5 |
| `--format` | Output format: `summary` or `json` | `summary` |

## Output

The skill returns a JSON object with:

- `action`: requested operation
- `command`: command ScienceClaw would run or did run
- `executed`: whether a command was executed
- `returncode`, `stdout`, and `stderr` when executed
- `pid` and `log_file` for detached server runs
- `checks` for local Node/npm/npx availability

## Notes

- Requires Node.js, npm, and npx. Paperclip currently documents Node.js 20+ as the expected runtime.
- `onboard --yes` uses Paperclip's non-interactive quickstart defaults.
- Rerunning onboarding should preserve an existing Paperclip configuration; use Paperclip's own configuration commands for later edits.
