"""Unit tests for the versioned command doc schema and loader."""

import pytest

from flac_mcp.knowledge.commands.loader import CommandLoader


class TestLoadCommandDocVersioned:
    """Tests for CommandLoader.load_command_doc with versioned JSON schema."""

    def setup_method(self):
        CommandLoader.clear_cache()

    def test_version_specific_fields_merged_to_top_level(self):
        doc = CommandLoader.load_command_doc("model", "new", "9.0")
        assert doc is not None
        assert "command" in doc
        assert "syntax" in doc
        assert "keywords" in doc
        assert "examples" in doc

    def test_version_field_values_are_correct(self):
        doc = CommandLoader.load_command_doc("zone", "create", "9.0")
        assert doc["command"] == "zone create"
        assert "zone create" in doc["syntax"]
        assert isinstance(doc["keywords"], list)
        assert len(doc["keywords"]) > 0

    def test_shared_fields_remain_at_top_level(self):
        doc = CommandLoader.load_command_doc("zone", "create", "9.0")
        assert "description" in doc
        assert "search_keywords" in doc
        assert "category" in doc
        assert isinstance(doc["search_keywords"], list)

    def test_versions_collapsed_to_list(self):
        doc = CommandLoader.load_command_doc("zone", "create", "9.0")
        assert "versions" in doc
        assert isinstance(doc["versions"], list)
        assert "9.0" in doc["versions"]

    def test_unknown_version_raises_key_error(self):
        with pytest.raises(KeyError, match="5.0"):
            CommandLoader.load_command_doc("zone", "create", "5.0")

    def test_version_6_0_loads_correctly(self):
        doc = CommandLoader.load_command_doc("model", "new", "6.0")
        assert doc is not None
        assert doc["command"] == "model new"
        assert "syntax" in doc
        assert isinstance(doc["keywords"], list)
        assert len(doc["keywords"]) > 0
        assert "6.0" in doc["versions"]

    def test_unknown_command_returns_none(self):
        result = CommandLoader.load_command_doc("zone", "nonexistent_cmd", "9.0")
        assert result is None

    def test_unknown_category_returns_none(self):
        result = CommandLoader.load_command_doc("nonexistent_cat", "create", "9.0")
        assert result is None

    def test_default_version_is_9_0(self):
        doc_default = CommandLoader.load_command_doc("zone", "create")
        doc_explicit = CommandLoader.load_command_doc("zone", "create", "9.0")
        assert doc_default["command"] == doc_explicit["command"]
        assert doc_default["syntax"] == doc_explicit["syntax"]

    def test_model_category_versioned(self):
        """Model commands are the primary target for multi-version support."""
        doc = CommandLoader.load_command_doc("model", "new", "9.0")
        assert doc is not None
        assert "command" in doc
        assert "syntax" in doc

    def test_keywords_list_contains_name_and_syntax(self):
        doc = CommandLoader.load_command_doc("zone", "create", "9.0")
        kw = doc["keywords"][0]
        assert "name" in kw
        assert "syntax" in kw

    def test_examples_list_contains_command_field(self):
        doc = CommandLoader.load_command_doc("model", "new", "9.0")
        ex = doc["examples"][0]
        assert "command" in ex
