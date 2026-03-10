# tests/test_config.py
# Tests for centralized configuration module.

import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config


class TestConfigDefaults:
    def test_llm_routing_model(self):
        assert config.LLM_ROUTING_MODEL == "llama-3.1-8b-instant"

    def test_llm_orchestrator_model(self):
        assert config.LLM_ORCHESTRATOR_MODEL == "gpt-oss-20b"

    def test_specialist_timeout(self):
        assert config.SPECIALIST_TIMEOUT_SECONDS == 60

    def test_tool_cache_ttl(self):
        assert config.TOOL_CACHE_TTL_SECONDS == 300

    def test_embedding_dimension(self):
        assert config.EMBEDDING_DIMENSION == 384

    def test_memory_long_term_max(self):
        assert config.MEMORY_LONG_TERM_MAX == 500

    def test_project_root_exists(self):
        assert config.PROJECT_ROOT.exists()

    def test_data_dir_exists(self):
        assert config.DATA_DIR.exists()


class TestConfigOverrides:
    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TOOL_CACHE_TTL", "600")
        # Re-import to pick up env change
        import importlib
        importlib.reload(config)
        assert config.TOOL_CACHE_TTL_SECONDS == 600
        # Reset
        monkeypatch.delenv("TOOL_CACHE_TTL", raising=False)
        importlib.reload(config)


class TestConfigValidation:
    def test_validate_with_groq_key_set(self, monkeypatch):
        monkeypatch.setenv("GROQ_API_KEY", "test-key")
        import importlib
        importlib.reload(config)
        errors = config.validate_config()
        # Should have no GROQ_API_KEY error
        assert not any("GROQ_API_KEY" in e for e in errors)

    def test_validate_without_groq_key(self, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        import importlib
        importlib.reload(config)
        errors = config.validate_config()
        assert any("GROQ_API_KEY" in e for e in errors)
        # Restore
        monkeypatch.setenv("GROQ_API_KEY", "restore")
        importlib.reload(config)

    def test_validate_returns_list(self):
        errors = config.validate_config()
        assert isinstance(errors, list)

    def test_validate_bad_specialist_timeout(self, monkeypatch):
        monkeypatch.setenv("SPECIALIST_TIMEOUT", "-1")
        import importlib
        importlib.reload(config)
        errors = config.validate_config()
        assert any("SPECIALIST_TIMEOUT" in e for e in errors)
        monkeypatch.delenv("SPECIALIST_TIMEOUT", raising=False)
        importlib.reload(config)
