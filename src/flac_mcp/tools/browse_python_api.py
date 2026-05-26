"""FLAC Python API Browse Tool - Navigate and retrieve Python SDK documentation."""

from typing import Any

from fastmcp import FastMCP
from pydantic import Field

from flac_mcp.contracts import build_docs_data, build_error, build_ok, wrap_payload
from flac_mcp.knowledge.compatibility import FLACProduct, normalize_product
from flac_mcp.knowledge.python_api import APILoader
from flac_mcp.knowledge.python_api.product_index import normalize_api_version, source_info
from flac_mcp.utils import CommandDocVersion


def register(mcp: FastMCP) -> None:
    """Register flac_browse_python_api tool with the MCP server."""

    @mcp.tool()
    def flac_browse_python_api(
        api: str | None = Field(
            None,
            description=(
                "FLAC Python API path to browse (dot-separated, starting from itasca). Examples:\n"
                "- None or '': Root overview - all modules and objects\n"
                "- 'itasca': Core module functions (command, cycle, gravity, etc.)\n"
                "- 'itasca.zone': Zone module functions (find, list, count, etc.)\n"
                "- 'itasca.zone.list': Specific function documentation\n"
                "- 'itasca.zone.Zone': Zone object method groups\n"
                "- 'itasca.zone.Zone.stress': Specific method documentation\n"
                "- 'itasca.gridpoint.Gridpoint': Gridpoint object method groups"
            ),
        ),
        product: FLACProduct = Field(
            FLACProduct.ANY,
            description=("FLAC product/dimension API index. Use 'flac2d' to browse the FLAC2D API set."),
        ),
        version: CommandDocVersion = Field(
            CommandDocVersion.V9_0,
            description="FLAC Python API documentation version. Bundled product-scoped API data is currently 9.0.",
        ),
    ) -> dict[str, Any]:
        """Browse FLAC Python SDK documentation by path (like glob + cat)."""
        normalized = _normalize_api_path(api)
        product_value = normalize_product(product)
        version_value = normalize_api_version(str(version.value if hasattr(version, "value") else version))
        source = source_info(product_value, version_value)
        if product_value != FLACProduct.ANY.value and not source.get("applicable", False):
            return build_error(
                code="product_version_not_applicable",
                message=f"{product_value} {version_value} is not applicable in the bundled FLAC Python API matrix.",
                details={
                    "source": "python_api",
                    "action": "browse",
                    "input": {"product": product_value, "version": version_value},
                    "availability": source,
                },
            )

        if not normalized:
            return build_ok(_browse_root(product_value, version_value))

        if normalized == "itasca":
            return wrap_payload(_browse_module("itasca", product_value, version_value))

        parsed = _parse_api_path(normalized, product_value, version_value)

        if parsed["type"] == "error":
            return wrap_payload(_browse_with_fallback(parsed, normalized, product_value, version_value))

        if parsed["type"] == "module":
            payload = _browse_module(parsed["module_path"], product_value, version_value)
            return wrap_payload(payload)
        if parsed["type"] == "function":
            payload = _browse_function(parsed["module_path"], parsed["name"], product_value, version_value)
            return wrap_payload(payload)
        if parsed["type"] == "object":
            payload = _browse_object(
                parsed["module_path"],
                parsed["name"],
                parsed.get("display_name"),
                product_value,
                version_value,
            )
            return wrap_payload(payload)
        if parsed["type"] == "method":
            payload = _browse_method(
                parsed["module_path"],
                parsed["object_name"],
                parsed["name"],
                parsed.get("display_name"),
                product_value,
                version_value,
            )
            return wrap_payload(payload)

        return build_error(
            code="unknown_parse_type",
            message=f"Unknown parse result type: {parsed['type']}",
            details={"path": normalized},
        )


def _normalize_api_path(api: str | None) -> str:
    if api is None:
        return ""
    return api.strip()


def _parse_api_path(api: str, product: str, version: str) -> dict[str, Any]:
    if not api.startswith("itasca"):
        return {
            "type": "error",
            "error": f"Path must start with 'itasca', got: {api}",
            "fallback_path": "",
        }

    parts = api.split(".")
    index = APILoader.load_index(product, version)
    modules = index.get("modules", {})
    objects = index.get("objects", {})

    object_index = None
    for i, part in enumerate(parts):
        if i > 0 and part[0].isupper():
            object_index = i
            break

    if object_index is not None:
        module_parts = parts[:object_index]
        module_path = ".".join(module_parts)
        object_name = parts[object_index]

        if object_name not in objects:
            return {
                "type": "error",
                "error": f"Object '{object_name}' not found",
                "fallback_path": module_path,
            }

        if len(parts) == object_index + 1:
            return {
                "type": "object",
                "module_path": module_path,
                "name": object_name,
                "display_name": object_name,
            }

        method_name = parts[object_index + 1]
        return {
            "type": "method",
            "module_path": module_path,
            "object_name": object_name,
            "display_name": object_name,
            "name": method_name,
        }

    for length in range(len(parts), 0, -1):
        candidate = ".".join(parts[:length])
        index_key = _path_to_index_key(candidate)

        if index_key in modules:
            if length == len(parts):
                return {
                    "type": "module",
                    "module_path": candidate,
                }

            func_name = parts[length]
            return {
                "type": "function",
                "module_path": candidate,
                "name": func_name,
            }

    return {
        "type": "error",
        "error": f"Module path not found: {api}",
        "fallback_path": ".".join(parts[:-1]) if len(parts) > 1 else "",
    }


def _path_to_index_key(full_path: str) -> str:
    if full_path == "itasca":
        return "itasca"
    if full_path.startswith("itasca."):
        return full_path[7:]
    return full_path


def _format_module_path(index_key: str) -> str:
    if index_key == "itasca":
        return "itasca"
    return f"itasca.{index_key}"


def _runtime_usage_note(module_path: str, product: str = FLACProduct.ANY.value) -> dict[str, str] | None:
    parts = module_path.split(".")
    if len(parts) == 2 and parts[1].endswith("array"):
        attr = parts[1]
        note = {
            "access": f"import itasca as it; it.{attr}.<function>(...)",
            "note": (
                "FLAC exposes this API as an attribute on the itasca extension module at runtime; "
                f"do not use 'import itasca.{attr}'."
            ),
        }
        if attr in {"zonearray", "gridpointarray"}:
            note["dimension"] = (
                "Position and vector arrays follow the active product dimension at runtime: "
                "FLAC2D returns two components, FLAC3D returns three components."
            )
            if product == FLACProduct.FLAC2D.value:
                note["active_product_shape"] = "FLAC2D runtime arrays use 2 columns for position/vector values."
            elif product == FLACProduct.FLAC3D.value:
                note["active_product_shape"] = "FLAC3D runtime arrays use 3 columns for position/vector values."
        return note
    return None


def _extract_function_names(functions: list[Any]) -> list[str]:
    names: list[str] = []
    for func in functions:
        if isinstance(func, dict):
            name = func.get("name")
            if name:
                names.append(name)
        elif isinstance(func, str):
            names.append(func)
    return names


def _module_summary(module_data: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in module_data.items() if key != "functions"}


def _browse_root(product: str, version: str) -> dict[str, Any]:
    index = APILoader.load_index(product, version)
    modules = index.get("modules", {})
    objects = index.get("objects", {})

    module_items: list[dict[str, Any]] = []
    for module_key, module_info in modules.items():
        path = _format_module_path(module_key)
        entry = {
            "entry_type": "module",
            "path": path,
            "description": module_info.get("description", ""),
            "function_count": len(module_info.get("functions", [])),
        }
        runtime_usage = _runtime_usage_note(path, product)
        if runtime_usage:
            entry["runtime_usage"] = runtime_usage
        module_items.append(entry)

    object_items: list[dict[str, Any]] = []
    for object_name, object_info in objects.items():
        object_items.append(
            {
                "entry_type": "object",
                "name": object_name,
                "description": object_info.get("description", ""),
                "file": object_info.get("file"),
                "types": object_info.get("types"),
            }
        )

    entries = module_items + object_items
    return build_docs_data(
        source="python_api",
        action="browse",
        entries=entries,
        summary={
            "count": len(entries),
            "total_modules": len(module_items),
            "total_objects": len(object_items),
            "product": product,
            "version": version,
            "source": index.get("source", {}),
        },
    )


def _browse_module(module_path: str, product: str, version: str) -> dict[str, Any]:
    index_key = _path_to_index_key(module_path)
    module_data = APILoader.load_module(index_key, product, version)

    if not module_data:
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "module_not_found",
                "message": f"Module not found: {module_path}",
            },
            "input": {"module_path": module_path},
        }

    index = APILoader.load_index(product, version)
    objects = index.get("objects", {})
    related_objects = []
    for obj_name, obj_data in objects.items():
        file_path = obj_data.get("file", "")
        if index_key in file_path or (index_key == "itasca" and "/" not in file_path):
            related_objects.append(obj_name)

    function_names = _extract_function_names(module_data.get("functions", []))

    summary = {
        "count": len(function_names),
        "module_path": module_path,
        "module": _module_summary(module_data),
        "related_objects": sorted(related_objects),
        "product": product,
        "version": version,
        "source": index.get("source", {}),
    }
    runtime_usage = _runtime_usage_note(module_path, product)
    if runtime_usage:
        summary["runtime_usage"] = runtime_usage

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[{"entry_type": "function", "name": name} for name in function_names],
        summary=summary,
    )


def _browse_function(module_path: str, func_name: str, product: str, version: str) -> dict[str, Any]:
    index_key = _path_to_index_key(module_path)
    func_doc = APILoader.load_function(index_key, func_name, product, version)

    if not func_doc:
        if product != FLACProduct.ANY.value and APILoader.load_function(index_key, func_name):
            return _api_unavailable_payload(
                "Function",
                func_name,
                {"module_path": module_path, "function": func_name, "product": product, "version": version},
            )
        module_data = APILoader.load_module(index_key, product, version) or {}
        available_functions = _extract_function_names(module_data.get("functions", []))
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "function_not_found",
                "message": f"Function '{func_name}' not found in {module_path}",
            },
            "input": {"module_path": module_path, "function": func_name},
            "available_functions": available_functions,
        }

    entry = {
        "module_path": module_path,
        "function": func_name,
        "availability": func_doc.get("availability", {}),
        "doc": func_doc,
    }
    runtime_usage = _runtime_usage_note(module_path, product)
    if runtime_usage:
        entry["runtime_usage"] = runtime_usage

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[entry],
        summary={"count": 1, "product": product, "version": version},
    )


def _browse_object(
    module_path: str,
    object_name: str,
    display_name: str | None = None,
    product: str = FLACProduct.ANY.value,
    version: str = "9.0",
) -> dict[str, Any]:
    object_doc = APILoader.load_object(object_name, product, version)
    shown_name = display_name or object_name

    if not object_doc:
        index = APILoader.load_index(product, version)
        available_objects = sorted(index.get("objects", {}).keys())
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "object_not_found",
                "message": f"Object not found: {shown_name}",
            },
            "input": {"module_path": module_path, "object": shown_name},
            "available_objects": available_objects,
        }

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[
            {
                "module_path": module_path,
                "object": shown_name,
                "actual_object": object_name,
                "availability": object_doc.get("availability", {}),
                "doc": object_doc,
            }
        ],
        summary={"count": 1, "product": product, "version": version},
    )


def _browse_method(
    module_path: str,
    object_name: str,
    method_name: str,
    display_name: str | None = None,
    product: str = FLACProduct.ANY.value,
    version: str = "9.0",
) -> dict[str, Any]:
    method_doc = APILoader.load_method(object_name, method_name, product, version)
    shown_name = display_name or object_name

    if not method_doc:
        if product != FLACProduct.ANY.value and APILoader.load_method(object_name, method_name):
            return _api_unavailable_payload(
                "Method",
                method_name,
                {
                    "module_path": module_path,
                    "object": shown_name,
                    "actual_object": object_name,
                    "method": method_name,
                    "product": product,
                    "version": version,
                },
            )
        object_doc = APILoader.load_object(object_name, product, version) or {}
        method_names = _extract_function_names(object_doc.get("methods", []))
        return {
            "source": "python_api",
            "action": "browse",
            "error": {
                "code": "method_not_found",
                "message": f"Method '{method_name}' not found in {shown_name}",
            },
            "input": {
                "module_path": module_path,
                "object": shown_name,
                "actual_object": object_name,
                "method": method_name,
            },
            "available_methods": method_names,
        }

    return build_docs_data(
        source="python_api",
        action="browse",
        entries=[
            {
                "module_path": module_path,
                "object": shown_name,
                "actual_object": object_name,
                "method": method_name,
                "availability": method_doc.get("availability", {}),
                "doc": method_doc,
            }
        ],
        summary={"count": 1, "product": product, "version": version},
    )


def _api_unavailable_payload(kind: str, name: str, input_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": "python_api",
        "action": "browse",
        "error": {
            "code": "api_unavailable_for_product",
            "message": f"{kind} '{name}' is not in the requested product/version API index.",
        },
        "input": input_data,
    }


def _browse_with_fallback(parsed: dict[str, Any], requested_api: str, product: str, version: str) -> dict[str, Any]:
    error_msg = parsed.get("error", "Unknown error")
    fallback_path = parsed.get("fallback_path", "")

    index = APILoader.load_index(product, version)
    modules = index.get("modules", {})
    available_modules = sorted(_format_module_path(module_key) for module_key in modules)

    return {
        "source": "python_api",
        "action": "browse",
        "error": {
            "code": "invalid_path",
            "message": error_msg,
        },
        "input": {"api": requested_api},
        "fallback_path": fallback_path or "itasca",
        "available_modules": available_modules,
    }
