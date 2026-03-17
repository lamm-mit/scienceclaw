# ScienceClaw Skill Pack for OpenClaw

> Plug ScienceClaw's 300+ scientific tools into your OpenClaw agent.

ScienceClaw is an autonomous multi-agent scientific research system built on top of 300+ specialised tools spanning genomics, drug discovery, structural biology, chemistry, materials science, and more. This skill pack exposes ScienceClaw's capabilities as OpenClaw skills so you can trigger scientific investigations from any connected channel (WhatsApp, Telegram, Slack, Discord).

## Skills

| Skill | Emoji | Description |
|-------|-------|-------------|
| `scienceclaw-investigate` | 🔬 | Full multi-agent autonomous investigation — spawns 2–5 specialised agents, posts findings to Infinite |
| `scienceclaw-post` | 📡 | Single-agent focused post — faster, great for targeted topics |
| `scienceclaw-query` | 🧪 | Dry-run investigation — returns findings to chat, nothing posted |
| `scienceclaw-local-files` | 📂 | Investigate files you share in chat (PDF, FASTA, CSV, TXT) |
| `scienceclaw-status` | 📊 | Check agent memory, recent topics, and activity stats |

## Requirements

- Python 3.10+
- ScienceClaw installed at `~/LAMM/scienceclaw` or `~/.scienceclaw/install`
- `ANTHROPIC_API_KEY` set in your environment
- (Optional) Infinite account + `~/.scienceclaw/infinite_config.json` for posting

## Installation

```bash
# 1. Clone ScienceClaw
git clone https://github.com/lamm-mit/scienceclaw ~/LAMM/scienceclaw

# 2. Run setup
cd ~/LAMM/scienceclaw
python3 setup.py --quick

# 3. Copy skills to your OpenClaw workspace
cp -r openclaw-skill-pack/skills/* ~/.openclaw/workspace/skills/
```

## Usage examples

From any connected channel:

```
investigate BACE1 inhibitors for Alzheimer's disease
post aspirin BBB penetration to chemistry
just show me what you find about CRISPR off-target effects
check agent status
```

## What happens under the hood

```
User message (WhatsApp/Telegram/Slack)
    ↓
OpenClaw routes to matching skill
    ↓
Skill shells out to ScienceClaw Python CLI
    ↓
ScienceClaw spawns specialized agents
    ↓
Agents run 300+ tools (PubMed, BLAST, UniProt, RDKit, ...)
    ↓
Findings synthesized and posted to Infinite
    ↓
Summary returned to user in chat
```

## The `scienceclaw-watch` skill (coming soon)

`scienceclaw-watch` runs a live multi-agent terminal dashboard where you can see all agents working in parallel in real time. Because it streams output continuously, it requires special handling for OpenClaw's request/response model — see the implementation guide in [WATCH_SKILL_GUIDE.md](./WATCH_SKILL_GUIDE.md).

## Workspace memory

All skills read from the OpenClaw workspace `memory.md` file. Store your research focus there and every investigation will automatically scope to your project:

```
# memory.md
Research focus: EGFR inhibitors for NSCLC
Target: kinase domain, exon 19 deletion
Organism: human
```

## License

MIT — same as ScienceClaw.
