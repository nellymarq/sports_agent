# tests/test_memory_api.py
# Unit tests for MemoryStore: decay, dedup, cap, read/write.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import time
from memory.memory_api import MemoryStore
from data.metadata import Evidence


class TestMemoryStoreBasics:
    def test_write_and_read_short_term(self):
        store = MemoryStore()
        store.write_short_term({"query": "test"})
        recent = store.get_recent_short_term(10)
        assert len(recent) == 1
        assert recent[0]["query"] == "test"
        assert "timestamp" in recent[0]

    def test_write_and_read_long_term(self):
        store = MemoryStore()
        store.write_long_term({"content": "analysis result"})
        items = store.get_long_term()
        assert len(items) == 1
        assert "hash" in items[0]

    def test_write_evidence(self):
        store = MemoryStore()
        ev = Evidence.create(source="test", content="test evidence")
        store.write_evidence(ev)
        assert len(store.get_evidence()) == 1

    def test_write_specialist_note(self):
        store = MemoryStore()
        store.write_specialist_note("style", {"content": "style analysis"})
        history = store.get_specialist_history("style")
        assert len(history) == 1
        assert "timestamp" in history[0]

    def test_specialist_history_empty(self):
        store = MemoryStore()
        assert store.get_specialist_history("nonexistent") == []

    def test_short_term_ordering(self):
        store = MemoryStore()
        store.write_short_term({"order": 1})
        time.sleep(0.01)
        store.write_short_term({"order": 2})
        recent = store.get_recent_short_term(10)
        # Most recent first
        assert recent[0]["order"] == 2


class TestMemoryDecay:
    def test_decay_long_term(self):
        store = MemoryStore()
        # Add an old item (fake timestamp)
        store.long_term.append({"timestamp": time.time() - 100, "hash": "old"})
        store.long_term.append({"timestamp": time.time(), "hash": "new"})
        store.decay_long_term(threshold_seconds=50)
        assert len(store.long_term) == 1
        assert store.long_term[0]["hash"] == "new"

    def test_decay_short_term(self):
        store = MemoryStore()
        store.short_term.append({"timestamp": time.time() - 200000})
        store.short_term.append({"timestamp": time.time()})
        store.decay_short_term(threshold_seconds=86400)
        assert len(store.short_term) == 1

    def test_decay_empty_store(self):
        store = MemoryStore()
        store.decay_long_term(threshold_seconds=100)
        store.decay_short_term(threshold_seconds=100)
        assert store.long_term == []
        assert store.short_term == []


class TestMemoryDedup:
    def test_dedupe_long_term(self):
        store = MemoryStore()
        item = {"content": "test", "timestamp": time.time(), "schema_version": "1.0.0"}
        item["hash"] = "abc123"
        store.long_term.append(item.copy())
        store.long_term.append(item.copy())
        store.long_term.append(item.copy())
        store.dedupe_long_term()
        assert len(store.long_term) == 1


class TestMemoryCap:
    def test_cap_long_term(self):
        store = MemoryStore()
        for i in range(10):
            store.long_term.append({"timestamp": time.time() + i, "hash": f"h{i}"})
        store.cap_long_term(max_entries=5)
        assert len(store.long_term) == 5
        # Most recent should be kept
        assert store.long_term[0]["hash"] == "h9"

    def test_cap_under_limit(self):
        store = MemoryStore()
        store.long_term.append({"timestamp": time.time(), "hash": "h1"})
        store.cap_long_term(max_entries=500)
        assert len(store.long_term) == 1


class TestMemoryFindSimilar:
    def test_find_similar_returns_empty_on_empty_store(self):
        store = MemoryStore()
        assert store.find_similar("test") == []

    def test_find_similar_with_data(self):
        store = MemoryStore()
        store.write_long_term({"content": "Conor McGregor knockout power analysis"})
        store.write_long_term({"content": "Weather forecast for tomorrow"})
        # Substring fallback should match the first item
        results = store.find_similar("McGregor", threshold=0.8)
        assert any("McGregor" in str(r.get("content", "")) for r in results)

    def test_cluster_topics_returns_empty_on_empty_store(self):
        store = MemoryStore()
        assert store.cluster_topics() == {}

    def test_cluster_topics_groups_by_type(self):
        store = MemoryStore()
        store.long_term.append({"type": "episodic", "content": "a", "timestamp": 1, "hash": "h1"})
        store.long_term.append({"type": "episodic", "content": "b", "timestamp": 2, "hash": "h2"})
        store.long_term.append({"type": "semantic", "content": "c", "timestamp": 3, "hash": "h3"})
        clusters = store.cluster_topics()
        assert "episodic" in clusters
        assert "semantic" in clusters
        assert len(clusters["episodic"]) == 2
        assert len(clusters["semantic"]) == 1

    def test_cluster_topics_defaults_to_general(self):
        store = MemoryStore()
        store.long_term.append({"content": "no type", "timestamp": 1, "hash": "h1"})
        clusters = store.cluster_topics()
        assert "general" in clusters
