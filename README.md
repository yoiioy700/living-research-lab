# Living Research Lab

A self-growing research intelligence system built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.

Living Research Lab extends Hermes Agent with a persistent knowledge base and a structured research protocol. It spawns parallel subagents to gather intelligence from multiple sources simultaneously, stores findings in a SQLite database, generates structured reports, and schedules recurring updates delivered to Telegram.

Built for the **Nous Research Hermes Agent Hackathon**.

---

## Features

- **Parallel research** — Spawns 3 subagents simultaneously to scrape web news, GitHub repositories, and community discussions (Reddit, Hacker News, arXiv)
- **Persistent knowledge base** — All findings are stored in a SQLite database (`~/.hermes/research.db`) and persist across sessions
- **Structured reports** — Generates Markdown reports with executive summary, key findings, trend analysis, and sentiment breakdown
- **Automated daily updates** — Uses Hermes cron scheduler to repeat research daily and deliver results to Telegram
- **Historical comparison** — Each new report compares against previous findings to surface what changed
- **Multi-platform access** — Works from CLI, Telegram, Discord, Slack, or WhatsApp

---

## Quick Start

### Prerequisites

- Python 3.10+
- [OpenRouter API key](https://openrouter.ai) (free signup)
- [Firecrawl API key](https://firecrawl.dev) (free tier available)

### Installation

```bash
git clone https://github.com/yoiioy700/living-research-lab.git
cd living-research-lab

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[all]"
```

### Configuration

```bash
mkdir -p ~/.hermes

cat > ~/.hermes/.env << 'EOF'
OPENROUTER_API_KEY=sk-or-v1-your-key-here
FIRECRAWL_API_KEY=fc-your-key-here
EOF

hermes config set model google/gemini-2.0-flash-001
```

### Verify

```bash
hermes doctor
```

Confirm that `web`, `research`, and `delegation` toolsets show as available.

### Usage

```bash
# Add a research topic
hermes chat -q "Add a research topic called 'Bitcoin ETF' to the research database"

# Run a full research cycle (spawns 3 parallel subagents)
hermes chat -q "Research the latest developments in Solana DeFi ecosystem this week"
```

---

## Telegram Setup

To access the research agent from Telegram:

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram using `/newbot`
2. Get your numeric user ID via [@userinfobot](https://t.me/userinfobot)
3. Add the following to `~/.hermes/.env`:

```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ALLOWED_USERS=your-user-id
TELEGRAM_HOME_CHANNEL=your-user-id
```

4. Start the gateway:

```bash
hermes gateway
```

5. Send a message to your bot on Telegram to start a research session.

---

## Architecture

```
User request
  |
  v
Hermes Agent loads Living Research Lab skill (SKILL.md)
  |
  |-- research_db: register topic, check historical data
  |
  v
delegate_task (batch mode, 3 parallel subagents):
  |-- Web News Agent       (web_search + web_extract)
  |-- GitHub Agent         (GitHub repository search)
  |-- Community Agent      (Hacker News, Reddit, arXiv)
  |
  v
All findings saved to SQLite via research_db
  |
  v
Structured Markdown report generated
  |-- Executive Summary
  |-- Key Findings (categorized by source)
  |-- Trend Analysis and Sentiment
  |-- Comparison with previous report
  |
  v
Report saved as digest, cron job scheduled for daily updates
```

---

## Project Structure

This project is a fork of [hermes-agent](https://github.com/NousResearch/hermes-agent) with the following additions:

| File | Description |
|---|---|
| `tools/research_db_tool.py` | SQLite-backed research knowledge base with 7 operations: add_topic, save_finding, get_findings, list_topics, remove_topic, save_digest, get_last_digest |
| `skills/research/living-research-lab/SKILL.md` | Skill definition that teaches Hermes the full research orchestration protocol |
| `tests/tools/test_research_db_tool.py` | 23 unit tests covering all database operations |

Modified files:
- `toolsets.py` — Added `research_db` to core tool list
- `model_tools.py` — Added `research_db_tool` to tool discovery

---

## Tests

```bash
source .venv/bin/activate
python -m pytest tests/tools/test_research_db_tool.py -v
```

All 23 tests passing.

---

## License

Built on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.
