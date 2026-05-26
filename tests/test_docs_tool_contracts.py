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


def _contains_key(value, key: str) -> bool:
    if isinstance(value, dict):
        return key in value or any(_contains_key(item, key) for item in value.values())
    if isinstance(value, list):
        return any(_contains_key(item, key) for item in value)
    return False


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
async def test_browse_commands_accepts_mixed_case_paths() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "Zone Create", "version": "9.0"},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["entries"][0]["doc"]["command"] == "zone create"


@pytest.mark.asyncio
async def test_browse_commands_legacy_flac3d_command_docs_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "extruder block create", "version": "7.0", "product": "flac3d"},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    doc = data["entries"][0]["doc"]
    assert doc["command"] == "extrude block create"
    assert doc["legacy_documentation"]["availability_verified"] is True
    assert doc["legacy_documentation"]["syntax_basis"] == "official FLAC3D 7.0 detailed command page"
    assert "cmd_extrude.block.create.html" in doc["legacy_documentation"]["source_urls"][0]

    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "body edge delete", "version": "6.0", "product": "flac3d"},
    )
    payload = _parse_tool_payload(result)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "command_unavailable_for_version"


@pytest.mark.asyncio
async def test_browse_category_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "zone", "version": "9.0"},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]
    names = {entry["name"] for entry in data["entries"]}

    assert payload["ok"] is True
    assert data["summary"]["version"] == "9.0"
    assert "create" in names


@pytest.mark.asyncio
async def test_browse_category_filters_commands_by_product() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "zone", "version": "9.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)
    names = {entry["name"] for entry in payload["data"]["entries"]}

    assert payload["ok"] is True
    assert "create2d" in names
    assert "create" not in names


@pytest.mark.asyncio
async def test_browse_commands_filters_by_product() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "zone create2d", "version": "9.0", "product": "flac3d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "command_unavailable_for_product"


@pytest.mark.asyncio
async def test_browse_commands_filters_3d_zone_create_for_flac2d() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "zone create", "version": "9.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "command_unavailable_for_product"


@pytest.mark.asyncio
async def test_browse_commands_not_found_suggestions_are_product_filtered() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "zone not_a_real_command", "version": "9.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)
    details = payload["error"].get("details") or {}
    suggestions = set(details.get("available_commands") or [])

    assert payload["ok"] is False
    assert payload["error"]["code"] == "command_not_found"
    assert "create2d" in suggestions
    assert "create" not in suggestions


@pytest.mark.asyncio
async def test_query_command_filters_by_product() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_command",
        {"query": "create2d", "limit": 5, "version": "9.0", "product": "flac3d"},
    )
    payload = _parse_tool_payload(result)
    names = {entry["name"] for entry in payload["data"]["entries"]}

    assert payload["ok"] is True
    assert "zone create2d" not in names


@pytest.mark.asyncio
async def test_browse_commands_rejects_non_applicable_flac2d_legacy_version() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_commands",
        {"command": "model new", "version": "7.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "product_version_not_applicable"


@pytest.mark.asyncio
async def test_query_command_rejects_non_applicable_flac2d_legacy_version() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_command",
        {"query": "model new", "version": "7.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "product_version_not_applicable"


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
async def test_browse_python_api_generated_zonearray_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_python_api", {"api": "itasca.zonearray"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["summary"]["module_path"] == "itasca.zonearray"
    assert data["summary"]["count"] >= 1
    assert data["summary"]["runtime_usage"]["access"].startswith("import itasca as it; it.zonearray")
    assert "do not use 'import itasca.zonearray'" in data["summary"]["runtime_usage"]["note"]


@pytest.mark.asyncio
async def test_browse_python_api_array_function_runtime_usage_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_python_api", {"api": "itasca.zonearray.pos"})
    payload = _parse_tool_payload(result)
    entry = payload["data"]["entries"][0]

    assert payload["ok"] is True
    assert entry["function"] == "pos"
    assert entry["runtime_usage"]["access"].startswith("import itasca as it; it.zonearray")
    assert "FLAC2D returns two components" in entry["runtime_usage"]["dimension"]


@pytest.mark.asyncio
async def test_browse_python_api_array_function_flac2d_shape_note_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_python_api",
        {"api": "itasca.zonearray.pos", "product": "flac2d", "version": "9.0"},
    )
    payload = _parse_tool_payload(result)
    entry = payload["data"]["entries"][0]

    assert payload["ok"] is True
    assert entry["runtime_usage"]["active_product_shape"] == (
        "FLAC2D runtime arrays use 2 columns for position/vector values."
    )


@pytest.mark.asyncio
async def test_browse_python_api_generated_attach_method_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_python_api", {"api": "itasca.attach.Attach.extra"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["entries"][0]["actual_object"] == "Attach"
    assert data["entries"][0]["method"] == "extra"


@pytest.mark.asyncio
async def test_browse_python_api_filters_3d_api_for_flac2d() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_python_api",
        {"api": "itasca.gravity_z", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "api_unavailable_for_product"


@pytest.mark.asyncio
async def test_browse_python_api_filters_explicit_out_of_plane_method_for_flac2d() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_python_api",
        {"api": "itasca.zone.Zone.stress_prin_z", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "api_unavailable_for_product"


@pytest.mark.asyncio
async def test_browse_python_api_rejects_non_applicable_flac2d_legacy_version() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_python_api",
        {"api": "itasca", "version": "7.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "product_version_not_applicable"


@pytest.mark.asyncio
async def test_python_api_coverage_reports_missing_modules() -> None:
    result = await mcp._tool_manager.call_tool("flac_python_api_coverage", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert "flac2d" in data["products"]
    assert "flac3d" in data["products"]
    assert data["matrix"]["flac3d"]["9.0"]["complete"] is True
    assert data["matrix"]["flac3d"]["9.0"]["missing_modules"] == []
    assert data["matrix"]["flac3d"]["7.0"]["complete"] is True
    assert data["matrix"]["flac3d"]["7.0"]["api_entry_count"] >= 500
    assert data["matrix"]["flac3d"]["6.0"]["complete"] is True
    assert data["matrix"]["flac3d"]["6.0"]["api_entry_count"] >= 350
    assert not _contains_key(data, "docs_dir")


@pytest.mark.asyncio
async def test_command_coverage_reports_product_version_matrix() -> None:
    result = await mcp._tool_manager.call_tool("flac_command_coverage", {})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert "flac2d" in data["products"]
    assert "flac3d" in data["products"]
    assert data["bundled"]["command_count"] >= 500
    assert data["matrix"]["flac3d"]["9.0"]["complete"] is True
    assert data["matrix"]["flac3d"]["9.0"]["available_for_product_count"] >= 500
    assert data["matrix"]["flac3d"]["7.0"]["complete"] is True
    assert data["matrix"]["flac3d"]["7.0"]["missing_version_count"] == 0
    assert data["matrix"]["flac3d"]["7.0"]["available_for_product_count"] >= 450
    assert data["matrix"]["flac3d"]["6.0"]["complete"] is True
    assert data["matrix"]["flac3d"]["6.0"]["missing_version_count"] == 0
    assert data["matrix"]["flac3d"]["6.0"]["available_for_product_count"] >= 350
    assert data["matrix"]["flac2d"]["9.0"]["filtered_by_product_count"] >= 1
    assert data["matrix"]["flac2d"]["6.0"]["applicable"] is False
    assert data["matrix"]["flac2d"]["6.0"]["missing_version_count"] == 0
    assert data["matrix"]["flac2d"]["7.0"]["applicable"] is False
    assert data["matrix"]["flac2d"]["7.0"]["missing_version_count"] == 0


@pytest.mark.asyncio
async def test_browse_python_api_versioned_flac3d_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_python_api",
        {"api": "itasca.zone.Zone.flow_z", "product": "flac3d", "version": "7.0"},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["summary"]["version"] == "7.0"
    assert data["entries"][0]["method"] == "flow_z"


@pytest.mark.asyncio
async def test_query_python_api_no_results_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_python_api",
        {"query": "definitelynonexistentkeyword", "limit": 5},
    )
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    assert data["source"] == "python_api"
    assert data["action"] == "query"
    assert data["summary"]["count"] == 0
    assert data["entries"] == []


@pytest.mark.asyncio
async def test_query_python_api_filters_3d_api_for_flac2d() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_python_api",
        {"query": "gravity_z", "limit": 5, "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)
    paths = {entry["api_path"] for entry in payload["data"]["entries"]}

    assert payload["ok"] is True
    assert "itasca.gravity_z" not in paths


@pytest.mark.asyncio
async def test_query_python_api_filters_out_of_plane_methods_for_flac2d() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_python_api",
        {"query": "stress_prin_z", "limit": 10, "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)
    paths = {entry["api_path"] for entry in payload["data"]["entries"]}

    assert payload["ok"] is True
    assert "itasca.zone.Zone.stress_prin_z" not in paths


@pytest.mark.asyncio
async def test_query_python_api_rejects_non_applicable_flac2d_legacy_version() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_python_api",
        {"query": "zone", "version": "7.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "product_version_not_applicable"


@pytest.mark.asyncio
async def test_query_python_api_keeps_3d_api_for_flac3d() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_query_python_api",
        {"query": "gravity_z", "limit": 5, "product": "flac3d"},
    )
    payload = _parse_tool_payload(result)
    paths = {entry["api_path"] for entry in payload["data"]["entries"]}

    assert payload["ok"] is True
    assert "itasca.gravity_z" in paths


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
    assert "plot-items" in names
    assert "boundary-conditions" in names
    assert "initial-conditions" in names
    assert "structural-properties" in names
    assert "histories-and-results" in names
    assert "fish-intrinsics" in names
    assert "interface-and-joints" in names
    assert "geometry-data-table" in names
    assert "sketch-and-building-blocks" in names


@pytest.mark.asyncio
async def test_browse_reference_plot_items_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "plot-items"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    names = {e["name"] for e in data["entries"]}
    assert {"zone", "gridpoint", "structure"} <= names


@pytest.mark.asyncio
async def test_browse_reference_plot_item_sub_item_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "plot-items zone color-by"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    entry = data["entries"][0]
    assert entry["category"] == "plot-items"
    assert entry["item"] == "zone"
    assert entry["sub_item"] == "color-by"
    assert entry["doc"]["parent"] == "zone"


@pytest.mark.asyncio
async def test_browse_reference_boundary_conditions_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "boundary-conditions"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    names = {e["name"] for e in data["entries"]}
    assert {"mechanical-face", "gridpoint-fixity", "fluid-flow", "apply-modifiers"} <= names

    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference", {"topic": "boundary-conditions mechanical-face"}
    )
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]
    assert payload["ok"] is True
    assert "zone face apply" in doc["primary_commands"]
    families = {family["family"] for family in doc["condition_families"]}
    assert {"stress", "velocity", "reaction"} <= families


@pytest.mark.asyncio
async def test_browse_reference_initial_conditions_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference", {"topic": "initial-conditions stress-initialization"}
    )
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]

    assert payload["ok"] is True
    assert "zone initialize-stresses" in doc["primary_commands"]
    method_names = {method["name"] for method in doc["methods"]}
    assert "gravity stress with K0 ratio" in method_names


@pytest.mark.asyncio
async def test_browse_reference_structural_properties_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "structural-properties cable"})
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]

    assert payload["ok"] is True
    assert "structure cable property" in doc["primary_commands"]
    groups = {group["group"] for group in doc["property_groups"]}
    assert {"reinforcement material", "grout coupling"} <= groups


@pytest.mark.asyncio
async def test_browse_reference_histories_and_results_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "histories-and-results"})
    payload = _parse_tool_payload(result)
    data = payload["data"]

    assert payload["ok"] is True
    names = {e["name"] for e in data["entries"]}
    assert {"history-workflow", "zone-field-data", "results-export"} <= names

    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference", {"topic": "histories-and-results zone-field-data"}
    )
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]
    assert payload["ok"] is True
    field_groups = {group["group"] for group in doc["field_groups"]}
    assert {"kinematics", "stress-strain", "fluid-thermal"} <= field_groups
    assert "shear-maximum" in doc["quantity_names"]


@pytest.mark.asyncio
async def test_browse_reference_explicit_mixed_dimension_overrides_z_keyword_filter() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference",
        {"topic": "histories-and-results zone-field-data", "version": "9.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)
    entry = payload["data"]["entries"][0]

    assert payload["ok"] is True
    assert entry["compatibility"]["dimension"] == "mixed"
    assert entry["doc"]["name"] == "zone-field-data"


@pytest.mark.asyncio
async def test_browse_reference_fish_intrinsics_contract() -> None:
    result = await mcp._tool_manager.call_tool("flac_browse_reference", {"topic": "fish-intrinsics field-query"})
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]

    assert payload["ok"] is True
    assert "zone.field.get" in doc["primary_intrinsics"]
    steps = {step["step"] for step in doc["workflow"]}
    assert {"Select field", "Batch query"} <= steps


@pytest.mark.asyncio
async def test_browse_reference_interface_and_joints_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference", {"topic": "interface-and-joints zone-interface"}
    )
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]

    assert payload["ok"] is True
    assert "zone interface create" in doc["primary_commands"]
    groups = {group["group"] for group in doc["property_groups"]}
    assert {"stiffness", "strength"} <= groups


@pytest.mark.asyncio
async def test_browse_reference_geometry_data_table_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference", {"topic": "geometry-data-table geometry-workflow"}
    )
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]

    assert payload["ok"] is True
    assert "geometry import" in doc["primary_commands"]
    assert "stl" in doc["formats"]


@pytest.mark.asyncio
async def test_browse_reference_sketch_building_blocks_contract() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference",
        {"topic": "sketch-and-building-blocks sketch-workflow", "product": "flac2d", "version": "9.0"},
    )
    payload = _parse_tool_payload(result)
    doc = payload["data"]["entries"][0]["doc"]

    assert payload["ok"] is True
    assert "zone generate from-sketch" in doc["primary_commands"]

    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference",
        {"topic": "sketch-and-building-blocks building-blocks", "product": "flac2d", "version": "9.0"},
    )
    payload = _parse_tool_payload(result)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "item_unavailable_for_product"


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


@pytest.mark.asyncio
async def test_browse_reference_filters_z_position_for_flac2d() -> None:
    result = await mcp._tool_manager.call_tool(
        "flac_browse_reference",
        {"topic": "range-elements position-z", "version": "9.0", "product": "flac2d"},
    )
    payload = _parse_tool_payload(result)

    assert payload["ok"] is False
    assert payload["error"]["code"] == "item_unavailable_for_product"
