"""Contract tests for documentation tool response structures."""

import json

import pytest

from flac_mcp.server import mcp


def _parse_tool_payload(result) -> dict:
    assert result is not None
    assert len(result.content) > 0
    text = result.content[0].text
    assert text.startswith("{")
    return json.loads(text)


@pytest.mark.asyncio
async def test_browse_commands_root_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_commands", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert payload.get("error") is None
    assert data["source"] == "commands"
    assert data["action"] == "browse"
    assert isinstance(data["entries"], list)
    assert data["summary"]["count"] >= 1
    assert data["summary"]["total_commands"] >= 1
    # flac-mcp targets ITASCA 9.0; the command tools default to 9.0.
    assert data["summary"]["version"] == "9.0"


@pytest.mark.asyncio
async def test_browse_commands_not_found_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "zone not_a_real_command"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "command_not_found"
    details = payload["error"].get("details") or {}
    assert details["source"] == "commands"
    assert details["input"]["category"] == "zone"
    assert details["input"]["command"] == "not_a_real_command"
    assert isinstance(details.get("available_commands"), list)


@pytest.mark.asyncio
async def test_query_command_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_command",
        {"query": "zone create", "limit": 5},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "commands"
    assert data["action"] == "query"
    assert data["summary"]["count"] >= 1
    # Command tools default to 9.0 (current ITASCA Software release).
    assert data["summary"]["version"] == "9.0"
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) >= 1


@pytest.mark.asyncio
async def test_browse_commands_versioned_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "model new", "version": "6.0"},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["summary"]["version"] == "6.0"
    doc = data["entries"][0]["doc"]
    assert doc["syntax"] == "model new [force]"


@pytest.mark.asyncio
async def test_browse_category_filters_unavailable_commands_by_version() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "model", "version": "6.0"},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]
    names = {entry["name"] for entry in data["entries"]}

    assert payload["ok"] is True
    assert data["summary"]["version"] == "6.0"
    assert "new" in names


@pytest.mark.asyncio
async def test_query_command_versioned_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_command",
        {"query": "model new", "limit": 5, "version": "6.0"},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["summary"]["version"] == "6.0"
    assert len(data["entries"]) >= 1
    assert data["entries"][0]["syntax"] == "model new [force]"


@pytest.mark.asyncio
async def test_browse_python_api_root_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_python_api", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "python_api"
    assert data["action"] == "browse"
    assert isinstance(data["entries"], list)
    assert data["summary"]["total_modules"] >= 1
    assert data["summary"]["total_objects"] >= 1


@pytest.mark.asyncio
async def test_query_python_api_no_results_contract() -> None:
    # Query must avoid technical single chars (x/y/z/r/n/t) and English word
    # stems — the BM25 partial matcher otherwise hits substrings like "z" or
    # "defin" via prefix/substring rules in keyword_matcher.find_partial_matches.
    result = await mcp._tool_manager.call_tool(
        "flac_query_python_api",
        {"query": "qqwbflkmp", "limit": 5},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "python_api"
    assert data["action"] == "query"
    assert data["summary"]["count"] == 0
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_browse_reference_root_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "reference"
    assert data["action"] == "browse"
    assert data["summary"]["count"] >= 1
    assert isinstance(data["entries"], list)
    names = {e["name"] for e in data["entries"]}
    assert "constitutive-models" in names


@pytest.mark.asyncio
async def test_browse_reference_constitutive_models_category_contract() -> None:
    # No version arg: constitutive-models is version-agnostic, so the
    # reference tool's default (7.0) must NOT filter the FLAC 9.0 models out.
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "constitutive-models"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "reference"
    assert data["summary"]["count"] >= 30
    names = {e["name"] for e in data["entries"]}
    assert {"mohr-coulomb", "drucker-prager", "null"} <= names


@pytest.mark.asyncio
async def test_browse_reference_constitutive_model_item_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "constitutive-models mohr-coulomb"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert payload.get("error") is None
    doc = data["entries"][0]["doc"]
    assert doc["model"] == "mohr-coulomb"
    props = doc["property_groups"][0]["properties"]
    keywords = {p["keyword"] for p in props}
    # The exact gap the e2e exposed: 'zone property' vocabulary discoverable.
    assert {"young", "poisson", "cohesion", "friction", "tension"} <= keywords
    assert doc["usage"]["assign"].startswith("zone cmodel assign mohr-coulomb")
    # Dimension-agnostic model: no property carries a `dim` tag (absence
    # means valid in both FLAC2D and FLAC3D).
    assert all("dim" not in p for p in props)


@pytest.mark.asyncio
async def test_browse_reference_dim_tag_scoped_to_orientation_pair() -> None:
    # e2e found dip/dip-direction are FLAC3D-only (FLAC2D uses `angle`) but,
    # unlike xz/yz/-z, that is not evident from the keyword text — so only
    # this pair is tagged dim=3D; the 2D alternative and self-evident
    # out-of-plane keywords stay untagged.
    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference", {"topic": "constitutive-models ubiquitous-joint"}
    )
    payload = _parse_tool_payload(result)
    assert payload["ok"] is True
    props = {p["keyword"]: p for p in payload["data"]["entries"][0]["doc"]["property_groups"][0]["properties"]}

    assert props["dip"]["dim"] == "3D"
    assert props["dip-direction"]["dim"] == "3D"
    # FLAC2D alternative and self-evidently-3D keyword are NOT tagged.
    assert "dim" not in props["angle"]
    assert "dim" not in props["normal-z"]
