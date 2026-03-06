# Living Research Lab — Demo Script & Submission Guide

## Demo Video Script (~3 minutes)

### Scene 1: Introduction (30 seconds)

Record your terminal. Say or type:

> "Living Research Lab is a self-growing AI research agent built on Hermes Agent.
> It spawns parallel subagents, saves findings to a knowledge base, sets up
> smart alerts, and schedules daily updates to Telegram."

### Scene 2: First Research Run (60 seconds)

```bash
# Clean start
hermes chat -q "Research 'Solana DeFi' for me. Add it as a topic, set up alerts for sentiment_shift and volume_spike, spawn 3 parallel subagents to research web news, GitHub repos, and community discussions, save findings, run analytics, and generate a structured report."
```

What the viewer sees:
- research_db called 3x (add_topic + set_alert x2)
- 3 subagents spawning simultaneously with delegate_task
- Each subagent searching different sources (web, GitHub, community)
- Findings being saved to SQLite
- Structured report generated

### Scene 3: Check Database (30 seconds)

```bash
hermes chat -q "List all research topics and show analytics for Solana DeFi including sentiment breakdown and volume trends"
```

### Scene 4: Telegram Demo (30 seconds)

Show your phone or Telegram desktop:
- Send: "what's new in Solana DeFi?"
- Bot responds with findings from the database
- Show that alerts are active

### Scene 5: Wrap Up (30 seconds)

Show the GitHub repo:

> "The agent self-improves — when findings exceed 20, it automatically creates
> a dedicated skill. All code is open source at
> github.com/yoiioy700/living-research-lab"

---

## Submission Writeup (for Tweet)

```
Living Research Lab — a self-growing AI research agent built on @NousResearch Hermes Agent

What it does:
- Spawns 3 parallel subagents to research web, GitHub, and community sources simultaneously
- Stores findings in a persistent SQLite knowledge base
- Smart alerts: fires when sentiment shifts, volume spikes, or keywords appear
- Trend analytics with sentiment breakdown and volume comparison
- Auto-creates dedicated skills when findings exceed 20 (self-improvement)
- Schedules daily research updates delivered to Telegram

Built with: delegate_task, research_db (custom tool), schedule_cronjob, skill_manage

GitHub: https://github.com/yoiioy700/living-research-lab

#HermesAgent #NousResearch
```

---

## Submission Checklist

1. [ ] Record screen with demo (use OBS, Loom, or phone screen recorder)
2. [ ] Post tweet with video + writeup text above, tagging @NousResearch
3. [ ] Copy tweet link
4. [ ] Post tweet link in Discord #hermes-agent-hackathon-submissions channel
