# 🔬 Living Research Lab

**Self-growing AI research agent built on [Hermes Agent](https://github.com/NousResearch/hermes-agent)**

> Built for the Nous Research Hermes Agent Hackathon 🏆

Living Research Lab is an autonomous research intelligence system. Tell it a topic → it spawns 3 parallel subagents to scrape the web, GitHub, and community sources → saves findings to a persistent knowledge base → generates a structured report → schedules daily updates delivered to your Telegram.

---

## ✨ Features

| Feature | How It Works |
|---|---|
| 🔀 **Parallel Research** | Spawns 3 subagents simultaneously (Web News + GitHub + Community) |
| 🗄️ **Persistent Knowledge Base** | SQLite database stores all findings across sessions |
| 📊 **Structured Reports** | Executive Summary, Key Findings, Trend Analysis, Sentiment |
| ⏰ **Auto Daily Updates** | Cron scheduler runs research daily, delivers to Telegram |
| 📱 **Multi-Platform** | Works from CLI, Telegram, Discord, Slack, WhatsApp |
| 🧠 **Self-Improving** | Compares new data against historical findings to surface changes |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [OpenRouter API key](https://openrouter.ai) (free signup)
- [Firecrawl API key](https://firecrawl.dev) (free tier: 500 credits/month)

### 1. Clone & Install

```bash
git clone https://github.com/yoiioy700/living-research-lab.git
cd living-research-lab

# Install uv (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment & install
uv venv .venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[all]"
```

### 2. Configure API Keys

```bash
mkdir -p ~/.hermes
cat > ~/.hermes/.env << 'EOF'
OPENROUTER_API_KEY=sk-or-v1-your-key-here
FIRECRAWL_API_KEY=fc-your-key-here
EOF
```

### 3. Set Model

```bash
hermes config set model google/gemini-2.0-flash-001
```

### 4. Verify Setup

```bash
hermes doctor
```

You should see `✓ web`, `✓ research`, `✓ delegation` all green.

### 5. Run!

```bash
# Basic test — add a topic
hermes chat -q "Add a research topic called 'Bitcoin ETF' to the research database"

# Full research — spawns 3 parallel subagents
hermes chat -q "Research the latest developments in Solana DeFi ecosystem this week"
```

---

## 📱 Telegram Setup (Optional)

Talk to the research agent from your phone:

1. Create a bot: Message [@BotFather](https://t.me/BotFather) → `/newbot`
2. Get your User ID: Message [@userinfobot](https://t.me/userinfobot)
3. Add to `~/.hermes/.env`:

```bash
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_ALLOWED_USERS=YOUR_USER_ID
TELEGRAM_HOME_CHANNEL=YOUR_USER_ID
```

4. Start the gateway:

```bash
hermes gateway
```

5. Send a message to your bot on Telegram:

> "riset tentang AI Safety minggu ini"

---

## 🏗️ Architecture

```
User Message → Hermes Agent reads SKILL.md
  │
  ├── research_db(add_topic)
  ├── research_db(get_last_digest) — check history
  │
  ▼
delegate_task (3 PARALLEL subagents):
  ├── [1] Web News Agent      → web_search + web_extract
  ├── [2] GitHub Agent        → GitHub trending repos
  └── [3] Community Agent     → HN, Reddit, arXiv
  │
  ▼ (all 3 complete simultaneously)
  │
  ├── research_db(save_finding) × N  — persist to SQLite
  │
  ▼
Generate Markdown Report:
  ├── Executive Summary
  ├── Key Findings (Web / GitHub / Community)
  ├── Trend Analysis + Sentiment
  └── Knowledge Base Stats
  │
  ├── research_db(save_digest)
  ├── schedule_cronjob("every 24h", deliver="telegram")
  │
  ▼
Deliver (CLI output or Telegram message)
```

---

## 🧩 Components

| File | Description |
|---|---|
| `tools/research_db_tool.py` | SQLite persistence — 7 actions (add_topic, save_finding, get_findings, list_topics, remove_topic, save_digest, get_last_digest) |
| `skills/research/living-research-lab/SKILL.md` | Orchestration instructions — teaches Hermes the full research protocol |
| `toolsets.py` | Modified — added `research_db` to all platform toolsets |
| `model_tools.py` | Modified — added tool discovery for research_db |

---

## 🧪 Tests

```bash
source .venv/bin/activate
python -m pytest tests/tools/test_research_db_tool.py -v
# 23 tests, all passing ✅
```

---

## 📄 License

Built on top of [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous Research.
