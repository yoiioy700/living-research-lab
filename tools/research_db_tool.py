#!/usr/bin/env python3
"""
Research DB Tool — Persistent Research Knowledge Base

Provides a SQLite-backed database for storing and retrieving research findings
across sessions. Part of the "Living Research Lab" skill for the Nous Research
Hermes Agent Hackathon.

Database lives at: ~/.hermes/research.db

Tables:
    topics   — research topics being monitored
    findings — individual findings per topic (from web scraping)
    digests  — daily summary digests sent to the user

Usage by the agent:
    research_db(action="add_topic",   topic="Solana DeFi")
    research_db(action="save_finding", topic="Solana DeFi", data={"summary": "...", "source": "..."})
    research_db(action="get_findings", topic="Solana DeFi", days=7)
    research_db(action="list_topics")
    research_db(action="save_digest", topic="Solana DeFi", data={"digest": "...", "sent_to": "telegram"})
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Location of the database
_HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
_DB_PATH = _HERMES_HOME / "research.db"


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def _get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row_factory set to dict-like access."""
    _HERMES_HOME.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _init_db():
    """Initialize the database schema if it doesn't exist."""
    with _get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS topics (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL UNIQUE,
                description TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS findings (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id      INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                summary       TEXT    NOT NULL,
                source_url    TEXT,
                source_title  TEXT,
                sentiment     TEXT CHECK(sentiment IN ('positive', 'negative', 'neutral', NULL)),
                tags          TEXT,  -- JSON array of tags
                found_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS digests (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id   INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                content    TEXT    NOT NULL,
                sent_to    TEXT,
                created_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_findings_topic_date
                ON findings(topic_id, found_at);

            CREATE INDEX IF NOT EXISTS idx_digests_topic_date
                ON digests(topic_id, created_at);

            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id    INTEGER NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
                condition   TEXT    NOT NULL,  -- e.g. 'sentiment_shift', 'volume_spike', 'keyword'
                threshold   TEXT,              -- JSON config for the condition
                enabled     INTEGER NOT NULL DEFAULT 1,
                last_fired  TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)


# Initialize DB when module loads
try:
    _init_db()
except Exception as exc:
    logger.warning("research_db: could not init database: %s", exc)


# ---------------------------------------------------------------------------
# Action handlers
# ---------------------------------------------------------------------------

def _add_topic(conn: sqlite3.Connection, topic: str, data: Optional[Dict]) -> Dict:
    description = (data or {}).get("description", "")
    try:
        conn.execute(
            "INSERT OR IGNORE INTO topics (name, description) VALUES (?, ?)",
            (topic, description),
        )
        conn.execute(
            "UPDATE topics SET updated_at=datetime('now'), description=? WHERE name=?",
            (description, topic),
        )
        conn.commit()
        return {"success": True, "message": f"Topic '{topic}' added/updated."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _save_finding(conn: sqlite3.Connection, topic: str, data: Optional[Dict]) -> Dict:
    if not data:
        return {"success": False, "error": "'data' is required for save_finding."}

    summary = data.get("summary", "")
    if not summary:
        return {"success": False, "error": "'data.summary' is required."}

    # Auto-create topic if it doesn't exist
    conn.execute(
        "INSERT OR IGNORE INTO topics (name) VALUES (?)", (topic,)
    )

    row = conn.execute("SELECT id FROM topics WHERE name=?", (topic,)).fetchone()
    if not row:
        return {"success": False, "error": f"Could not find or create topic '{topic}'."}

    topic_id = row["id"]
    tags = json.dumps(data.get("tags", [])) if isinstance(data.get("tags"), list) else None

    conn.execute(
        """INSERT INTO findings (topic_id, summary, source_url, source_title, sentiment, tags)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            topic_id,
            summary,
            data.get("source_url"),
            data.get("source_title"),
            data.get("sentiment"),
            tags,
        ),
    )
    conn.commit()

    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=?", (topic_id,)
    ).fetchone()["cnt"]

    return {
        "success": True,
        "message": f"Finding saved under topic '{topic}'. Total findings: {count}.",
    }


def _get_findings(conn: sqlite3.Connection, topic: str, days: int) -> Dict:
    row = conn.execute("SELECT id FROM topics WHERE name=?", (topic,)).fetchone()
    if not row:
        return {"success": False, "error": f"Topic '{topic}' not found. Use add_topic first."}

    topic_id = row["id"]
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    findings = conn.execute(
        """SELECT summary, source_url, source_title, sentiment, tags, found_at
           FROM findings
           WHERE topic_id=? AND found_at >= ?
           ORDER BY found_at DESC""",
        (topic_id, since),
    ).fetchall()

    result_list = []
    for f in findings:
        entry = dict(f)
        if entry["tags"]:
            try:
                entry["tags"] = json.loads(entry["tags"])
            except Exception:
                pass
        result_list.append(entry)

    return {
        "success": True,
        "topic": topic,
        "days": days,
        "count": len(result_list),
        "findings": result_list,
    }


def _list_topics(conn: sqlite3.Connection) -> Dict:
    rows = conn.execute(
        """SELECT t.name, t.description, t.created_at,
                  COUNT(f.id) as finding_count,
                  MAX(f.found_at) as last_finding_at
           FROM topics t
           LEFT JOIN findings f ON f.topic_id = t.id
           GROUP BY t.id
           ORDER BY t.name"""
    ).fetchall()

    return {
        "success": True,
        "count": len(rows),
        "topics": [dict(r) for r in rows],
    }


def _remove_topic(conn: sqlite3.Connection, topic: str) -> Dict:
    result = conn.execute("DELETE FROM topics WHERE name=?", (topic,))
    conn.commit()
    if result.rowcount == 0:
        return {"success": False, "error": f"Topic '{topic}' not found."}
    return {"success": True, "message": f"Topic '{topic}' and all its findings removed."}


def _save_digest(conn: sqlite3.Connection, topic: str, data: Optional[Dict]) -> Dict:
    if not data:
        return {"success": False, "error": "'data' is required for save_digest."}

    content = data.get("digest", data.get("content", ""))
    if not content:
        return {"success": False, "error": "'data.digest' is required."}

    conn.execute("INSERT OR IGNORE INTO topics (name) VALUES (?)", (topic,))
    row = conn.execute("SELECT id FROM topics WHERE name=?", (topic,)).fetchone()
    if not row:
        return {"success": False, "error": f"Could not find or create topic '{topic}'."}

    conn.execute(
        "INSERT INTO digests (topic_id, content, sent_to) VALUES (?, ?, ?)",
        (row["id"], content, data.get("sent_to")),
    )
    conn.commit()
    return {"success": True, "message": f"Digest saved for topic '{topic}'."}


def _get_last_digest(conn: sqlite3.Connection, topic: str) -> Dict:
    row = conn.execute("SELECT id FROM topics WHERE name=?", (topic,)).fetchone()
    if not row:
        return {"success": False, "error": f"Topic '{topic}' not found."}

    digest = conn.execute(
        """SELECT content, sent_to, created_at FROM digests
           WHERE topic_id=? ORDER BY created_at DESC LIMIT 1""",
        (row["id"],),
    ).fetchone()

    if not digest:
        return {"success": True, "topic": topic, "digest": None, "message": "No digest found."}

    return {"success": True, "topic": topic, "digest": dict(digest)}


def _get_analytics(conn: sqlite3.Connection, topic: str, days: int) -> Dict:
    """Get analytics and trend data for a topic."""
    row = conn.execute("SELECT id FROM topics WHERE name=?", (topic,)).fetchone()
    if not row:
        return {"success": False, "error": f"Topic '{topic}' not found."}

    topic_id = row["id"]
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    prev_since = (datetime.now(timezone.utc) - timedelta(days=days * 2)).isoformat()

    # Current period counts
    current = conn.execute(
        "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=? AND found_at >= ?",
        (topic_id, since),
    ).fetchone()["cnt"]

    # Previous period counts (for comparison)
    previous = conn.execute(
        "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=? AND found_at >= ? AND found_at < ?",
        (topic_id, prev_since, since),
    ).fetchone()["cnt"]

    # Sentiment breakdown (current period)
    sentiments = conn.execute(
        """SELECT sentiment, COUNT(*) as cnt FROM findings
           WHERE topic_id=? AND found_at >= ? AND sentiment IS NOT NULL
           GROUP BY sentiment""",
        (topic_id, since),
    ).fetchall()
    sentiment_map = {s["sentiment"]: s["cnt"] for s in sentiments}
    total_with_sentiment = sum(sentiment_map.values())

    sentiment_pct = {}
    if total_with_sentiment > 0:
        for s in ["positive", "neutral", "negative"]:
            sentiment_pct[s] = round(sentiment_map.get(s, 0) / total_with_sentiment * 100, 1)

    # Top tags (current period)
    tag_rows = conn.execute(
        "SELECT tags FROM findings WHERE topic_id=? AND found_at >= ? AND tags IS NOT NULL",
        (topic_id, since),
    ).fetchall()
    tag_counts = {}
    for tr in tag_rows:
        try:
            for tag in json.loads(tr["tags"]):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        except Exception:
            pass
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Volume change
    volume_change = None
    if previous > 0:
        volume_change = round((current - previous) / previous * 100, 1)

    # Total all-time
    total_all_time = conn.execute(
        "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=?", (topic_id,)
    ).fetchone()["cnt"]

    # Digest count
    digest_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM digests WHERE topic_id=?", (topic_id,)
    ).fetchone()["cnt"]

    return {
        "success": True,
        "topic": topic,
        "period_days": days,
        "findings_this_period": current,
        "findings_previous_period": previous,
        "volume_change_pct": volume_change,
        "sentiment_breakdown": sentiment_pct,
        "top_tags": top_tags,
        "total_findings_all_time": total_all_time,
        "total_digests": digest_count,
        "should_create_skill": total_all_time >= 20,
        "skill_recommendation": (
            f"You have {total_all_time} findings on '{topic}'. "
            "Consider creating a dedicated skill using skill_manage to "
            "add specialized data sources, custom scrapers, or domain-specific "
            "analysis for this topic."
        ) if total_all_time >= 20 else None,
    }


def _set_alert(conn: sqlite3.Connection, topic: str, data: Optional[Dict]) -> Dict:
    """Set an alert condition for a topic."""
    if not data:
        return {"success": False, "error": "'data' is required. Include 'condition' and optional 'threshold'."}

    condition = data.get("condition", "")
    valid_conditions = ["sentiment_shift", "volume_spike", "keyword"]
    if condition not in valid_conditions:
        return {
            "success": False,
            "error": f"Invalid condition '{condition}'. Valid: {valid_conditions}",
        }

    conn.execute("INSERT OR IGNORE INTO topics (name) VALUES (?)", (topic,))
    row = conn.execute("SELECT id FROM topics WHERE name=?", (topic,)).fetchone()
    if not row:
        return {"success": False, "error": f"Could not find or create topic '{topic}'."}

    threshold = json.dumps(data.get("threshold", {})) if data.get("threshold") else None

    conn.execute(
        "INSERT INTO alerts (topic_id, condition, threshold) VALUES (?, ?, ?)",
        (row["id"], condition, threshold),
    )
    conn.commit()

    return {
        "success": True,
        "message": f"Alert set: '{condition}' on topic '{topic}'.",
        "condition": condition,
        "threshold": data.get("threshold"),
    }


def _check_alerts(conn: sqlite3.Connection, topic: str, days: int) -> Dict:
    """Check all alerts for a topic and return which ones would fire."""
    row = conn.execute("SELECT id FROM topics WHERE name=?", (topic,)).fetchone()
    if not row:
        return {"success": False, "error": f"Topic '{topic}' not found."}

    topic_id = row["id"]
    alerts = conn.execute(
        "SELECT id, condition, threshold FROM alerts WHERE topic_id=? AND enabled=1",
        (topic_id,),
    ).fetchall()

    if not alerts:
        return {"success": True, "topic": topic, "triggered": [], "message": "No alerts configured."}

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    prev_since = (datetime.now(timezone.utc) - timedelta(days=days * 2)).isoformat()

    triggered = []
    for alert in alerts:
        condition = alert["condition"]
        threshold_raw = alert["threshold"]
        threshold = json.loads(threshold_raw) if threshold_raw else {}

        if condition == "sentiment_shift":
            # Check if negative sentiment increased significantly
            current_neg = conn.execute(
                "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=? AND found_at >= ? AND sentiment='negative'",
                (topic_id, since),
            ).fetchone()["cnt"]
            prev_neg = conn.execute(
                "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=? AND found_at >= ? AND found_at < ? AND sentiment='negative'",
                (topic_id, prev_since, since),
            ).fetchone()["cnt"]
            min_increase = threshold.get("min_increase_pct", 50)
            if prev_neg > 0 and current_neg > prev_neg:
                increase = (current_neg - prev_neg) / prev_neg * 100
                if increase >= min_increase:
                    triggered.append({
                        "alert_id": alert["id"],
                        "condition": "sentiment_shift",
                        "message": f"Negative sentiment increased by {increase:.0f}% ({prev_neg} -> {current_neg} findings)",
                    })

        elif condition == "volume_spike":
            current_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=? AND found_at >= ?",
                (topic_id, since),
            ).fetchone()["cnt"]
            prev_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=? AND found_at >= ? AND found_at < ?",
                (topic_id, prev_since, since),
            ).fetchone()["cnt"]
            min_spike = threshold.get("min_spike_pct", 100)
            if prev_count > 0 and current_count > prev_count:
                spike = (current_count - prev_count) / prev_count * 100
                if spike >= min_spike:
                    triggered.append({
                        "alert_id": alert["id"],
                        "condition": "volume_spike",
                        "message": f"Finding volume spiked by {spike:.0f}% ({prev_count} -> {current_count})",
                    })

        elif condition == "keyword":
            keywords = threshold.get("keywords", [])
            for kw in keywords:
                matches = conn.execute(
                    "SELECT COUNT(*) as cnt FROM findings WHERE topic_id=? AND found_at >= ? AND summary LIKE ?",
                    (topic_id, since, f"%{kw}%"),
                ).fetchone()["cnt"]
                if matches > 0:
                    triggered.append({
                        "alert_id": alert["id"],
                        "condition": "keyword",
                        "message": f"Keyword '{kw}' found in {matches} recent finding(s)",
                    })

    # Update last_fired for triggered alerts
    for t in triggered:
        conn.execute(
            "UPDATE alerts SET last_fired=datetime('now') WHERE id=?",
            (t["alert_id"],),
        )
    conn.commit()

    return {
        "success": True,
        "topic": topic,
        "total_alerts": len(alerts),
        "triggered_count": len(triggered),
        "triggered": triggered,
        "action_required": len(triggered) > 0,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

_VALID_ACTIONS = {
    "add_topic", "save_finding", "get_findings",
    "list_topics", "remove_topic", "save_digest", "get_last_digest",
    "get_analytics", "set_alert", "check_alerts",
}


def research_db(
    action: str,
    topic: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
    days: int = 7,
) -> str:
    """
    Persistent research knowledge base backed by SQLite.

    All data is stored at ~/.hermes/research.db and persists across sessions.

    Actions:
        add_topic     — Register a new topic to monitor
        save_finding  — Store a research finding under a topic
        get_findings  — Retrieve findings for a topic (last N days)
        list_topics   — List all monitored topics with stats
        remove_topic  — Delete a topic and all its findings
        save_digest   — Store a generated digest/report
        get_last_digest — Get the most recent digest for a topic
    """
    if action not in _VALID_ACTIONS:
        return json.dumps({
            "success": False,
            "error": f"Unknown action '{action}'. Valid actions: {sorted(_VALID_ACTIONS)}",
        })

    needs_topic = action not in {"list_topics"}
    if needs_topic and not topic:
        return json.dumps({
            "success": False,
            "error": f"'topic' is required for action '{action}'.",
        })

    try:
        with _get_connection() as conn:
            if action == "add_topic":
                result = _add_topic(conn, topic, data)
            elif action == "save_finding":
                result = _save_finding(conn, topic, data)
            elif action == "get_findings":
                result = _get_findings(conn, topic, days)
            elif action == "list_topics":
                result = _list_topics(conn)
            elif action == "remove_topic":
                result = _remove_topic(conn, topic)
            elif action == "save_digest":
                result = _save_digest(conn, topic, data)
            elif action == "get_last_digest":
                result = _get_last_digest(conn, topic)
            elif action == "get_analytics":
                result = _get_analytics(conn, topic, days)
            elif action == "set_alert":
                result = _set_alert(conn, topic, data)
            elif action == "check_alerts":
                result = _check_alerts(conn, topic, days)
            else:
                result = {"success": False, "error": "Unreachable action."}

    except Exception as exc:
        logger.exception("research_db error in action '%s'", action)
        result = {"success": False, "error": str(exc)}

    return json.dumps(result, ensure_ascii=False, default=str)


def check_research_db_requirements() -> bool:
    """research_db has no external requirements — SQLite is stdlib."""
    return True


# ---------------------------------------------------------------------------
# OpenAI / Hermes Tool Schema
# ---------------------------------------------------------------------------

RESEARCH_DB_SCHEMA = {
    "name": "research_db",
    "description": (
        "Persistent research knowledge base that stores and retrieves research "
        "findings across sessions. Use this to build a growing knowledge base "
        "about any topic you are tracking.\n\n"

        "ACTIONS:\n"
        "- add_topic: Register a topic to monitor (topic='Solana DeFi')\n"
        "- save_finding: Save a research finding or bounty. Requires data.summary. Optional: "
        "data.source_url, data.source_title, data.sentiment ('positive'/'negative'/'neutral'), "
        "data.tags (list of strings, use ['bounty'] or ['open-issue'] for job/bounty findings)\n"
        "- get_findings: Get findings for a topic over last N days (default 7)\n"
        "- list_topics: List all monitored topics with finding counts\n"
        "- remove_topic: Delete a topic and all its findings\n"
        "- save_digest: Store a generated research report (data.digest required, "
        "optional data.sent_to)\n"
        "- get_last_digest: Get the most recent report for a topic\n"
        "- get_analytics: Get trend analytics — sentiment breakdown, volume changes, "
        "top tags, and auto-skill recommendation when findings exceed 20\n"
        "- set_alert: Configure smart alerts. data.condition can be: "
        "'sentiment_shift' (fires when negative sentiment increases), "
        "'volume_spike' (fires when finding count jumps), "
        "'keyword' (fires when specific keywords appear). Optional data.threshold for tuning.\n"
        "- check_alerts: Evaluate all alerts for a topic and return which ones triggered\n\n"

        "WHEN TO USE:\n"
        "- After gathering research from web: save_finding for each key discovery\n"
        "- Before generating a report: get_findings + get_analytics for full context\n"
        "- After generating a report: save_digest to track what was already reported\n"
        "- In cron jobs: check_alerts first, then get_findings + get_last_digest\n"
        "- When get_analytics returns should_create_skill=true: use skill_manage to "
        "create a dedicated skill for that topic with specialized data sources"
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": sorted(_VALID_ACTIONS),
                "description": "The database action to perform.",
            },
            "topic": {
                "type": "string",
                "description": (
                    "The research topic name (e.g. 'Solana DeFi', 'AI Safety', "
                    "'Bitcoin ETF'). Required for all actions except list_topics."
                ),
            },
            "data": {
                "type": "object",
                "description": (
                    "Action-specific payload. For save_finding: {summary, source_url, "
                    "source_title, sentiment, tags}. For save_digest: {digest, sent_to}. "
                    "For add_topic: {description}."
                ),
            },
            "days": {
                "type": "integer",
                "description": (
                    "For get_findings: how many days back to retrieve (default: 7)."
                ),
            },
        },
        "required": ["action"],
    },
}


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

from tools.registry import registry  # noqa: E402

registry.register(
    name="research_db",
    toolset="research",
    schema=RESEARCH_DB_SCHEMA,
    handler=lambda args, **kw: research_db(
        action=args.get("action", ""),
        topic=args.get("topic"),
        data=args.get("data"),
        days=int(args.get("days", 7)),
    ),
    check_fn=check_research_db_requirements,
)
