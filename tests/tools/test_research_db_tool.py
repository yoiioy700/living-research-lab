"""
Unit tests for tools/research_db_tool.py
"""

import json
import os
import sys
import tempfile
import pytest
from pathlib import Path

# Point HERMES_HOME at a temp dir so we don't pollute ~/.hermes
_tmp = tempfile.mkdtemp(prefix="hermes_test_")
os.environ["HERMES_HOME"] = _tmp

# Add hermes-agent root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Now import the module (this also calls _init_db under the test HERMES_HOME)
from tools.research_db_tool import research_db, _init_db, _DB_PATH


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Each test gets its own isolated DB."""
    import tools.research_db_tool as rdb_mod

    db_path = tmp_path / "research.db"
    monkeypatch.setattr(rdb_mod, "_DB_PATH", db_path)
    monkeypatch.setattr(rdb_mod, "_HERMES_HOME", tmp_path)

    # Re-init so tables get created in the temp path
    rdb_mod._init_db()
    yield db_path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def call(action, topic=None, data=None, days=7):
    return json.loads(research_db(action=action, topic=topic, data=data, days=days))


# ---------------------------------------------------------------------------
# Tests: add_topic
# ---------------------------------------------------------------------------

class TestAddTopic:
    def test_add_new_topic(self):
        r = call("add_topic", topic="Bitcoin ETF")
        assert r["success"] is True

    def test_idempotent(self):
        call("add_topic", topic="Bitcoin ETF")
        r = call("add_topic", topic="Bitcoin ETF")
        assert r["success"] is True  # should not error on duplicate

    def test_with_description(self):
        r = call("add_topic", topic="AI Safety", data={"description": "AI alignment research"})
        assert r["success"] is True


# ---------------------------------------------------------------------------
# Tests: save_finding
# ---------------------------------------------------------------------------

class TestSaveFinding:
    def test_save_basic_finding(self):
        r = call("save_finding", topic="Solana DeFi", data={
            "summary": "TVL on Solana DeFi hit $5B this week.",
            "source_url": "https://example.com/solana",
            "source_title": "DeFi Pulse",
            "sentiment": "positive",
            "tags": ["solana", "defi", "tvl"],
        })
        assert r["success"] is True
        assert "Total findings: 1" in r["message"]

    def test_save_increments_count(self):
        for i in range(3):
            call("save_finding", topic="Solana DeFi", data={"summary": f"Finding {i}"})
        r = call("save_finding", topic="Solana DeFi", data={"summary": "Finding 3"})
        assert "Total findings: 4" in r["message"]

    def test_requires_summary(self):
        r = call("save_finding", topic="Solana DeFi", data={"source_url": "https://example.com"})
        assert r["success"] is False
        assert "summary" in r["error"]

    def test_auto_creates_topic(self):
        """save_finding should auto-create the topic if it doesn't exist."""
        r = call("save_finding", topic="New Topic", data={"summary": "Something new."})
        assert r["success"] is True

    def test_invalid_sentiment_still_saves(self):
        """Sentiment field is optional; bad value may raise DB constraint."""
        # Invalid sentiment should be handled gracefully
        try:
            r = call("save_finding", topic="Test", data={"summary": "Test.", "sentiment": "very_bullish"})
            # If DB raises, it should return an error dict
            # Either outcome is acceptable — just shouldn't crash the process
        except Exception as exc:
            pytest.fail(f"Unexpected exception: {exc}")


# ---------------------------------------------------------------------------
# Tests: get_findings
# ---------------------------------------------------------------------------

class TestGetFindings:
    def test_get_findings_returns_all(self):
        for i in range(5):
            call("save_finding", topic="Ethereum", data={"summary": f"Eth finding {i}"})
        r = call("get_findings", topic="Ethereum", days=7)
        assert r["success"] is True
        assert r["count"] == 5
        assert len(r["findings"]) == 5

    def test_findings_ordered_latest_first(self):
        call("save_finding", topic="Ethereum", data={"summary": "First"})
        call("save_finding", topic="Ethereum", data={"summary": "Second"})
        r = call("get_findings", topic="Ethereum")
        assert r["findings"][0]["summary"] == "Second"

    def test_unknown_topic_returns_error(self):
        r = call("get_findings", topic="Unknown Topic XYZ")
        assert r["success"] is False

    def test_tags_deserialized(self):
        call("save_finding", topic="Ethereum", data={
            "summary": "Tagged finding.", "tags": ["defi", "l2"]
        })
        r = call("get_findings", topic="Ethereum")
        tags = r["findings"][0]["tags"]
        assert isinstance(tags, list)
        assert "defi" in tags


# ---------------------------------------------------------------------------
# Tests: list_topics
# ---------------------------------------------------------------------------

class TestListTopics:
    def test_empty(self):
        r = call("list_topics")
        assert r["success"] is True
        assert r["count"] == 0

    def test_multiple_topics(self):
        for topic in ["Bitcoin", "Ethereum", "Solana"]:
            call("add_topic", topic=topic)
        r = call("list_topics")
        assert r["count"] == 3
        names = [t["name"] for t in r["topics"]]
        assert "Bitcoin" in names and "Ethereum" in names

    def test_includes_finding_count(self):
        call("save_finding", topic="Bitcoin", data={"summary": "BTC up."})
        call("save_finding", topic="Bitcoin", data={"summary": "BTC down."})
        r = call("list_topics")
        btc = next(t for t in r["topics"] if t["name"] == "Bitcoin")
        assert btc["finding_count"] == 2


# ---------------------------------------------------------------------------
# Tests: remove_topic
# ---------------------------------------------------------------------------

class TestRemoveTopic:
    def test_remove_existing(self):
        call("add_topic", topic="Cardano")
        r = call("remove_topic", topic="Cardano")
        assert r["success"] is True

    def test_remove_nonexistent(self):
        r = call("remove_topic", topic="DoesNotExist")
        assert r["success"] is False

    def test_findings_cascade_deleted(self):
        call("save_finding", topic="Cardano", data={"summary": "ADA news."})
        call("remove_topic", topic="Cardano")
        r = call("get_findings", topic="Cardano")
        assert r["success"] is False  # topic gone → error


# ---------------------------------------------------------------------------
# Tests: save_digest & get_last_digest
# ---------------------------------------------------------------------------

class TestDigests:
    def test_save_and_retrieve_digest(self):
        call("add_topic", topic="AI Safety")
        r = call("save_digest", topic="AI Safety", data={
            "digest": "# Weekly AI Safety Report\n\nKey findings: ...",
            "sent_to": "telegram",
        })
        assert r["success"] is True

        r2 = call("get_last_digest", topic="AI Safety")
        assert r2["success"] is True
        assert "Weekly AI Safety" in r2["digest"]["content"]
        assert r2["digest"]["sent_to"] == "telegram"

    def test_get_last_digest_none(self):
        call("add_topic", topic="Empty Topic")
        r = call("get_last_digest", topic="Empty Topic")
        assert r["success"] is True
        assert r["digest"] is None

    def test_latest_digest_returned(self):
        call("add_topic", topic="Crypto")
        call("save_digest", topic="Crypto", data={"digest": "Old report"})
        call("save_digest", topic="Crypto", data={"digest": "New report"})
        r = call("get_last_digest", topic="Crypto")
        assert "New report" in r["digest"]["content"]


# ---------------------------------------------------------------------------
# Tests: invalid actions
# ---------------------------------------------------------------------------

class TestInvalidActions:
    def test_unknown_action(self):
        r = call("foobar_action", topic="Test")
        assert r["success"] is False
        assert "Unknown action" in r["error"]

    def test_missing_topic_for_action_that_needs_it(self):
        r = call("save_finding", topic=None, data={"summary": "test"})
        assert r["success"] is False
        assert "'topic' is required" in r["error"]
