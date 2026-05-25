from flac_mcp.config import get_bridge_config


def test_bridge_config_uses_flac_env(monkeypatch) -> None:
    monkeypatch.setenv("FLAC_MCP_RECONNECT_INTERVAL_S", "1.25")
    monkeypatch.setenv("FLAC_MCP_MAX_RETRIES", "4")
    monkeypatch.setenv("FLAC_MCP_REQUEST_TIMEOUT_S", "15")
    monkeypatch.setenv("FLAC_MCP_AUTO_RECONNECT", "false")

    config = get_bridge_config()

    assert config.reconnect_interval_s == 1.25
    assert config.max_retries == 4
    assert config.request_timeout_s == 15
    assert config.auto_reconnect is False
