---
name: living-research-lab
description: Self-growing research intelligence system with parallel subagents, persistent knowledge base, smart alerts, trend analytics, and auto-skill creation.
version: 2.0.0
metadata:
  hermes:
    tags: [research, intelligence, automation, parallel-agents, cron, telegram, knowledge-base, alerts, analytics]
    related_skills: [arxiv, duckduckgo-search]
---

# Living Research Lab

A self-growing research intelligence system. Each time you run it, Hermes:
1. Spawns 4 parallel subagents to gather intelligence (including open bounties/issues) simultaneously
2. Saves each finding to a persistent SQLite knowledge base via `research_db`
3. Checks smart alerts for significant changes (sentiment shifts, volume spikes, keywords)
4. Runs trend analytics — sentiment breakdown, volume comparison, top tags
5. Generates a structured Markdown report with Executive Summary, Key Findings, Open Bounties, and Trend Analysis
6. Schedules a recurring cron job (if not already set) to repeat daily and deliver to Telegram/Discord
7. When findings exceed 20, recommends creating a dedicated skill for that topic (self-improvement)

---

## When to Invoke

User says something like:
- "riset tentang [topic]"
- "pantau perkembangan [topic] tiap hari"
- "kasih gua report tentang [topic]"
- "apa yang baru di [topic] minggu ini?"
- "cariin open bounty atau paid issue untuk [topic]"
- "set alert kalo [topic] ada perubahan besar"
- `/living-research-lab [topic]`

---

## Step-by-Step Orchestration

### Step 1 — Check & Register Topic

```
research_db(action="add_topic", topic="<TOPIC>", data={"description": "<user's intent>"})
research_db(action="get_last_digest", topic="<TOPIC>")
research_db(action="get_analytics", topic="<TOPIC>", days=7)
```

Note the analytics output: sentiment trends, volume changes, and whether `should_create_skill` is true.

---

### Step 2 — Check Alerts (if any exist)

```
research_db(action="check_alerts", topic="<TOPIC>", days=7)
```

If any alerts triggered, include them prominently at the top of the report with an ALERT section.

---

### Step 3 — Spawn 4 Parallel Research Subagents

Use `delegate_task` in **batch mode** with exactly 4 tasks (the 4th is the Auto-Bounty Hunter):

```json
{
  "tasks": [
    {
      "goal": "Search the web for the latest news, updates, and developments about '<TOPIC>' from the last 7 days. Find at least 5 high-quality sources. For each source: extract title, URL, a 2-3 sentence summary of the key finding, and whether the sentiment is positive/negative/neutral. Return a JSON list of findings.",
      "toolsets": ["web"]
    },
    {
      "goal": "Search GitHub for active repositories, trending projects, and recent commits related to '<TOPIC>'. Use web_search with queries like 'site:github.com <TOPIC>' and 'github <TOPIC> 2025'. Return a JSON list with: repo name, URL, a brief description of what makes it relevant, and star count if available.",
      "toolsets": ["web"]
    },
    {
      "goal": "Search for technical discussions, forum posts, research papers, and expert opinions about '<TOPIC>'. Search Hacker News (hn.algolia.com), Reddit (reddit.com/search), and scholarly sources. Return a JSON list of: title, URL, 2-3 sentence summary, and sentiment (positive/negative/neutral).",
      "toolsets": ["web"]
    },
    {
      "goal": "Act as an Auto-Bounty Hunter. Search GitHub, Gitcoin, Bounties Network, or other platforms for open bounties, paid issues, or job opportunities related to '<TOPIC>'. Use web_search with queries like 'site:github.com <TOPIC> label:bounty OR label:\"good first issue\"' AND 'open bounty <TOPIC>'. Return a JSON list of: issue/bounty title, URL, reward/context summary, and tag it with 'bounty' or 'open-issue'.",
      "toolsets": ["web"]
    }
  ]
}
```

Wait for all 4 to complete.

---

### Step 4 — Persist All Findings

For **each finding** returned by each subagent:

```
research_db(
  action="save_finding",
  topic="<TOPIC>",
  data={
    "summary": "<2-3 sentence finding>",
    "source_url": "<url>",
    "source_title": "<title>",
    "sentiment": "positive" | "negative" | "neutral",
    "tags": ["<relevant-tag>", ...]
  }
)
```

Save ALL findings even if similar ones were found before.

---

### Step 5 — Generate Structured Report

Retrieve combined data and write a structured report:

```
research_db(action="get_findings", topic="<TOPIC>", days=7)
research_db(action="get_analytics", topic="<TOPIC>", days=7)
research_db(action="get_last_digest", topic="<TOPIC>")
```

**Report format (STRICTLY follow this template):**

```markdown
# Research Lab Report: <TOPIC>
Generated: <date>  |  Sources this run: <N>  |  Total in DB: <total>

---

## ALERTS (only if check_alerts returned triggered items)
- [ALERT TYPE]: [alert message]

## Executive Summary
[2-4 sentences: what's the biggest takeaway this week]

## Key Findings
### Web News
- **[Source Title]** — [1-sentence finding] ([link])
- ...

### GitHub Activity
- **[Repo Name]** — [1-sentence relevance] ([link])
- ...

### Community & Research
- **[Post/Paper Title]** — [1-sentence finding] ([link])
- ...

## 💰 Open Bounties & Issues (If Any)
- **[Bounty/Issue Title]** — [Reward/Context] ([link])
- ...

## Trend Analysis
Sentiment: [X% positive / Y% neutral / Z% negative]
Volume change: [+/-X% vs previous period]
Top tags: [tag1, tag2, tag3]
What changed since last report: [compare with historical data]

## Knowledge Base Stats
- Total findings in DB: <N>
- First tracked: <date>
- Last report sent: <date or "None">
- Active alerts: <count>
- Skill recommendation: [if should_create_skill is true, mention it]

---
Report auto-generated by Living Research Lab
```

---

### Step 6 — Save Digest & Schedule Cron

**Save the report:**
```
research_db(
  action="save_digest",
  topic="<TOPIC>",
  data={"digest": "<the full markdown report>", "sent_to": "telegram"}
)
```

**Set up default alerts** if none exist for this topic:
```
research_db(action="set_alert", topic="<TOPIC>", data={"condition": "sentiment_shift", "threshold": {"min_increase_pct": 50}})
research_db(action="set_alert", topic="<TOPIC>", data={"condition": "volume_spike", "threshold": {"min_spike_pct": 100}})
```

**Check if cron already exists** before scheduling (to avoid duplicates):
```
list_cronjobs()
```

If no cron for this topic exists, schedule a daily update:
```
schedule_cronjob(
  prompt="Generate a Living Research Lab report about '<TOPIC>'. First check_alerts, then spawn 4 parallel subagents with delegate_task to gather fresh intelligence + bounties. Save all findings to research_db, run get_analytics, generate a structured report, save the digest, and deliver the report.",
  schedule="every 24h",
  name="LRL: <TOPIC>",
  deliver="telegram"
)
```

---

### Step 7 — Auto Skill Creation (Self-Improvement)

If `get_analytics` returned `should_create_skill: true` (20+ findings on a topic):

1. Analyze the top tags and most common source domains from the findings
2. Use `skill_manage` to create a new dedicated skill for the topic:

```
skill_manage(
  action="create",
  name="<topic-slug>-research",
  content="---\nname: <topic-slug>-research\ndescription: Specialized research skill for <TOPIC> ...\n---\n\n# <TOPIC> Specialized Research\n\nThis skill was auto-generated by Living Research Lab after collecting 20+ findings.\n\n## Specialized Data Sources\n[List domain-specific sources discovered from findings, e.g. specific APIs, dashboards, data feeds]\n\n## Custom Analysis\n[Topic-specific analysis instructions based on most common tags and patterns]\n"
)
```

3. Tell the user: "I've created a dedicated skill for '<TOPIC>' based on accumulated research data. Future research on this topic will use specialized data sources."

---

### Step 8 — Deliver Report

Return the full Markdown report as your final response. If running via messaging platform, the structured Markdown will render beautifully.

---

## Key Rules

- **ALWAYS** use `delegate_task` in batch mode (4 parallel tasks) — never research sequentially
- **ALWAYS** save findings to `research_db` before generating the report
- **ALWAYS** run `check_alerts` before the report to surface urgent changes
- **ALWAYS** run `get_analytics` for trend data and skill recommendations
- **ALWAYS** compare with historical data (get_last_digest + get_findings with days=30)
- **NEVER** create a duplicate cron job — check `list_cronjobs` first
- **NEVER** skip setting up default alerts for new topics
- If `research_db` returns an error (DB not available), proceed without it but note this in the report

---

## Example Invocations

```
User: "riset tentang Solana DeFi"
-> Check alerts (none yet, first time)
-> Spawn 4 subagents (Web + GitHub + Community + Bounty Hunter)
-> Save findings to DB with topic="Solana DeFi"
-> Run analytics (first run, no historical comparison)
-> Generate report (including 💰 Open Bounties section)
-> Set default alerts (sentiment_shift + volume_spike)
-> Schedule daily cron "every 24h" to Telegram

User: "apa yang baru di AI Safety minggu ini?"
-> check_alerts: sentiment_shift triggered (negative +60%)
-> get_findings for last 7 days
-> Spawn 4 subagents for fresh data
-> get_analytics: 25 total findings, should_create_skill=true
-> Generate report with ALERT section at top
-> Auto-create dedicated "ai-safety-research" skill

User: "set alert kalo Bitcoin ada berita tentang ETF"
-> set_alert(topic="Bitcoin", data={"condition": "keyword", "threshold": {"keywords": ["ETF", "SEC", "approval"]}})
-> Confirm: "Alert set. I'll notify you when 'ETF', 'SEC', or 'approval' appears in Bitcoin research findings."
```
