# Living Research Lab

A self-growing research intelligence system built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.

> **The agent not only aggregates info — it learns what matters over time.**

It spawns 4 parallel subagents, stores findings with trust scoring, detects anomalies, auto-evolves topics, hunts for bounties, and delivers structured reports on schedule via Telegram.

Built for the **Nous Research Hermes Agent Hackathon**.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🚀 **4 Parallel Subagents** | Web News, GitHub, Community, and Bounty Hunter run simultaneously |
| 🧠 **Signal vs Noise** | Trust scoring per source domain, composite ranking (trust × recency × engagement) |
| 🔬 **Anomaly Detection** | Flags volume spikes (>200%), sentiment flips, new dominant tags |
| 🌱 **Auto-Topic Evolution** | Suggests and auto-creates sub-topics when tag clusters reach threshold |
| 💰 **Bounty Hunter** | Finds open bounties, paid issues, and job opportunities on GitHub/Gitcoin |
| 💾 **Persistent Knowledge Base** | SQLite database persists across sessions (`~/.hermes/research.db`) |
| 📊 **Structured Reports** | Executive summary, key findings, anomalies, bounties, trend analysis |
| ⏰ **Automated Daily Updates** | Cron scheduler repeats research and delivers to Telegram |
| 🛠️ **Auto-Skill Creation** | When 20+ findings accumulate, generates a dedicated specialized skill |

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

curl -LsSf https://astral.sh/uv/install.sh | sh
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

---

## 🎯 Preset Workflows

### 1. Crypto Research Mode

Track the fast-moving crypto ecosystem with parallel intelligence gathering + bounty hunting.

```bash
# Step 1: Add your crypto topics
hermes chat -q "Add these research topics: 'Bitcoin ETF', 'Solana DeFi', 'Ethereum L2'"

# Step 2: Run a full research cycle (spawns 4 parallel subagents)
hermes chat -q "Research Bitcoin ETF developments this week. Include open bounties."

# Step 3: Check what anomalies were detected
hermes chat -q "Run detect_anomalies on Bitcoin ETF and show me the results"

# Step 4: See what sub-topics the agent discovered
hermes chat -q "Suggest subtopics for Bitcoin ETF based on recent findings"

# Step 5: Schedule daily updates to Telegram
hermes chat -q "Schedule a daily cron job for Bitcoin ETF research, deliver to Telegram"
```

**Example output:** See [`docs/examples/bitcoin-etf-report.md`](docs/examples/bitcoin-etf-report.md)

### 2. LLM Ecosystem Tracker

Monitor the rapidly evolving LLM landscape — new models, benchmarks, open-source releases.

```bash
# Step 1: Add LLM topics
hermes chat -q "Add these research topics: 'OpenAI GPT', 'Anthropic Claude', 'Open Source LLMs', 'LLM Benchmarks'"

# Step 2: Run research with signal scoring
hermes chat -q "Research Open Source LLMs. After saving findings, score them and show me the top 5 highest-signal items."

# Step 3: Detect anomalies (e.g. new model drops, benchmark leaps)
hermes chat -q "Detect anomalies for Open Source LLMs over the last 14 days"

# Step 4: Auto-evolve topics
hermes chat -q "Suggest subtopics for Open Source LLMs. Auto-add any with 5+ mentions."
```

---

## Architecture

```
User request
  │
  ▼
Hermes Agent loads Living Research Lab skill (SKILL.md)
  │
  ├── research_db: register topic, check alerts, detect anomalies
  │
  ▼
delegate_task (batch mode, 4 parallel subagents):
  ├── Web News Agent       (web_search + web_extract)
  ├── GitHub Agent         (repository + commit search)
  ├── Community Agent      (Hacker News, Reddit, arXiv)
  └── 💰 Bounty Hunter     (GitHub issues, Gitcoin, bounty platforms)
  │
  ▼
All findings saved to SQLite with auto-computed trust scores
  │
  ├── score_findings → rank by trust × recency × engagement
  ├── detect_anomalies → flag volume spikes, sentiment flips, new tags
  ├── suggest_subtopics → auto-evolve research scope
  │
  ▼
Structured Markdown report generated (v3.0):
  ├── 🚨 Alerts & Anomalies
  ├── Executive Summary (from top-scored findings)
  ├── Key Findings (Web / GitHub / Community)
  ├── 💰 Open Bounties & Issues
  ├── 📈 Trend Analysis & Sentiment
  ├── 🌱 Suggested Sub-Topics
  └── Knowledge Base Stats
  │
  ▼
Report saved as digest → cron job scheduled → delivered via Telegram
```

---

## Telegram Setup

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

---

## Project Structure

This project is a fork of [hermes-agent](https://github.com/NousResearch/hermes-agent) with the following additions:

| File | Description |
|---|---|
| `tools/research_db_tool.py` | SQLite-backed KB: 13 operations including trust scoring, anomaly detection, signal ranking, auto-topic evolution |
| `skills/research/living-research-lab/SKILL.md` | Full orchestration protocol: 4 parallel subagents, anomaly detection, scoring, auto-evolution |
| `tests/tools/test_research_db_tool.py` | 23 unit tests covering all database operations |
| `docs/examples/` | Example reports showing real output format |

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
