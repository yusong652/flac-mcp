"""Documentation formatters for FLAC Python SDK docs."""

from typing import Any

from flac_mcp.knowledge.python_api.loader import DocumentationLoader
from flac_mcp.knowledge.python_api.types.mappings import CLASS_TO_MODULE


class APIDocFormatter:
    """Formats API documentation as LLM-friendly markdown."""

    @staticmethod
    def format_with_error(error_msg: str, fallback_content: str) -> str:
        """Prepend an error message to fallback content."""
        return f"Error: {error_msg}\n\n{fallback_content}"

    @staticmethod
    def _index_key_to_path(index_key: str) -> str:
        if index_key == "itasca":
            return "itasca"
        return f"itasca.{index_key}"

    @staticmethod
    def format_root(modules: dict[str, Any], objects: dict[str, Any]) -> str:
        """Format root overview of all modules and objects."""
        module_lines = []
        for key, data in modules.items():
            full_path = APIDocFormatter._index_key_to_path(key)
            desc = _trim(data.get("description", ""))
            module_lines.append(f"- {full_path} ({len(data.get('functions', []))} funcs): {desc}")

        object_lines = []
        for name, data in objects.items():
            module_name = CLASS_TO_MODULE.get(name)
            obj_path = f"itasca.{module_name}.{name}" if module_name else name
            object_lines.append(f"- {obj_path}: {_trim(data.get('description', ''))}")

        return "\n".join(
            [
                "## FLAC Python SDK Documentation",
                "",
                f"Modules ({len(modules)}):",
                "\n".join(module_lines),
                "",
                f"Objects ({len(object_lines)}):",
                "\n".join(object_lines),
            ]
        )

    @staticmethod
    def format_module(module_path: str, module_data: dict[str, Any], related_objects: list[str] | None = None) -> str:
        """Format module overview with its functions."""
        functions = module_data.get("functions", [])
        func_lines = []
        for func in functions:
            if isinstance(func, dict):
                func_lines.append(f"- {func.get('name', '')}: {_trim(func.get('description', ''), 60)}")
            else:
                func_lines.append(f"- {func}")

        parts = [f"## {module_path}", ""]
        if module_data.get("description"):
            parts.extend([module_data["description"], ""])
        parts.extend([f"Functions ({len(func_lines)}):", "\n".join(func_lines)])
        if related_objects:
            parts.extend(["", f"Related Objects: {', '.join(f'{module_path}.{obj}' for obj in related_objects)}"])
        return "\n".join(parts)

    @staticmethod
    def format_object(
        module_path: str,
        object_name: str,
        object_doc: dict[str, Any],
        display_name: str | None = None,
    ) -> str:
        """Format object overview with its method groups."""
        shown_name = display_name or object_name
        method_lines = _method_group_lines(object_doc)
        parts = [f"## {module_path}.{shown_name}", ""]
        if object_doc.get("description"):
            parts.append(object_doc["description"])
        if object_doc.get("note"):
            parts.extend(["", f"Note: {object_doc['note']}"])
        parts.extend(["", "Method Groups:", "\n".join(method_lines)])
        return "\n".join(parts)

    @staticmethod
    def format_signature(api_name: str, metadata: dict[str, Any] | None = None) -> str | None:
        """Format a brief one-line signature for quick reference."""
        api_doc = DocumentationLoader.load_api_doc(api_name)
        if not api_doc:
            return None

        brief_desc = api_doc["description"].strip().split("\n")[0].strip()
        signature = api_doc["signature"]
        if "->" not in signature and api_doc.get("returns"):
            signature = f"{signature} -> {api_doc['returns']['type']}"

        component_suffix = ""
        if metadata and "has_components" in metadata:
            components = metadata["has_components"]
            component_suffix = f" [has _{', _'.join(components)} components]"

        return f"`{signature}` - {brief_desc}{component_suffix}"

    @staticmethod
    def format_full_doc(api_doc: dict[str, Any], api_name: str, metadata: dict[str, Any] | None = None) -> str:
        """Format complete API documentation."""
        lines = [f"# {APIDocFormatter._get_display_path(api_name)}", ""]

        if metadata and "has_components" in metadata:
            components = metadata["has_components"]
            method_name = api_name.split(".")[-1]
            lines.append(f"**Component Access**: {', '.join(f'`{method_name}_{c}()`' for c in components)}")
            lines.append("")

        lines.extend([f"**Signature**: `{api_doc['signature']}`", "", api_doc["description"], ""])
        _append_parameters(lines, api_doc)
        _append_returns(lines, api_doc)
        _append_examples(lines, api_doc)
        _append_list_section(lines, "Limitations", api_doc.get("limitations"))
        if api_doc.get("fallback_commands"):
            lines.extend([f"**When to use commands instead**: {', '.join(api_doc['fallback_commands'])}", ""])
        _append_list_section(lines, "Best Practices", api_doc.get("best_practices"), bullet=True)
        _append_list_section(lines, "Notes", api_doc.get("notes"), bullet=True)
        if api_doc.get("see_also"):
            lines.extend([f"**See Also**: {', '.join(api_doc['see_also'])}", ""])
        return "\n".join(lines)

    @staticmethod
    def _get_display_path(api_name: str, metadata: dict[str, Any] | None = None) -> str:
        """Generate official API path for display."""
        if "." in api_name and not api_name.startswith("itasca."):
            class_name = api_name.split(".")[0]
            if class_name in CLASS_TO_MODULE:
                return f"itasca.{CLASS_TO_MODULE[class_name]}.{api_name}"
        return api_name

    @staticmethod
    def format_no_results_response(query: str, hints: list[str] | None = None) -> str:
        """Format LLM content when no Python SDK API is found."""
        hint_text = f"\nNote: {hints[0]}" if hints else ""
        return f"**Python SDK**: Not available for '{query}'{hint_text}"

    @staticmethod
    def format_function(func_doc: dict[str, Any], module_path: str) -> str:
        """Format function documentation for the browse tool."""
        name = func_doc.get("name", "")
        signature = func_doc.get("signature", f"{module_path}.{name}()")
        lines = [
            f"## {module_path}.{name}",
            "",
            f"Signature: `{signature}`",
            "",
            func_doc.get("description", ""),
            "",
        ]
        _append_parameters(lines, func_doc, compact=True)
        _append_returns(lines, func_doc, compact=True)
        _append_list_section(lines, "Limitations", func_doc.get("limitations"), compact=True)
        _append_examples(lines, func_doc, first_only=True)
        return "\n".join(lines)

    @staticmethod
    def format_method(method_doc: dict[str, Any], object_name: str, actual_object_name: str | None = None) -> str:
        """Format method documentation for the browse tool."""
        name = method_doc.get("name", "")
        lines = [
            f"## {object_name}.{name}",
            "",
            f"Signature: `{method_doc.get('signature', f'{object_name.lower()}.{name}()')}`",
            "",
            method_doc.get("description", ""),
            "",
        ]
        _append_parameters(lines, method_doc, compact=True)
        _append_returns(lines, method_doc, compact=True)
        components = APIDocFormatter._detect_component_methods(actual_object_name or object_name, name)
        if components:
            lines.extend([f"Component Access: {', '.join(f'`{name}_{c}()`' for c in components)}", ""])
        _append_examples(lines, method_doc, first_only=True)
        return "\n".join(lines)

    @staticmethod
    def _detect_component_methods(object_name: str, method_name: str) -> list[str]:
        """Detect whether a method has _x/_y/_z component alternatives."""
        try:
            object_doc = DocumentationLoader.load_object(object_name)
        except Exception:
            return []
        if not object_doc:
            return []

        all_method_names = set()
        for group_methods in object_doc.get("method_groups", {}).values():
            if isinstance(group_methods, list):
                all_method_names.update(group_methods)
        for method in object_doc.get("methods", []):
            all_method_names.add(method.get("name", "") if isinstance(method, dict) else str(method))

        if method_name not in all_method_names:
            return []
        return [component for component in ("x", "y", "z") if f"{method_name}_{component}" in all_method_names]


def _trim(text: str, max_len: int = 50) -> str:
    return text[: max_len - 3] + "..." if len(text) > max_len else text


def _method_group_lines(object_doc: dict[str, Any]) -> list[str]:
    method_lines = []
    method_groups = object_doc.get("method_groups", {})
    if method_groups:
        for group_name, group_methods in method_groups.items():
            if isinstance(group_methods, list):
                method_list = ", ".join(group_methods[:5])
                if len(group_methods) > 5:
                    method_list += f", ... (+{len(group_methods) - 5})"
                method_lines.append(f"- {group_name}: {method_list}")
            else:
                method_lines.append(f"- {group_name}: {group_methods}")
        return method_lines

    method_names = [
        method.get("name", str(method)) if isinstance(method, dict) else str(method)
        for method in object_doc.get("methods", [])
    ]
    for i in range(0, len(method_names), 5):
        method_lines.append(f"  {', '.join(method_names[i : i + 5])}")
    return method_lines


def _append_parameters(lines: list[str], doc: dict[str, Any], *, compact: bool = False) -> None:
    params = doc.get("parameters", [])
    if not params:
        return
    lines.append("Parameters:" if compact else "## Parameters")
    for param in params:
        required = "required" if compact else "**required**"
        optional = "optional" if compact else "*optional*"
        req = required if param.get("required") else optional
        lines.append(
            f"- **`{param.get('name', '')}`** ({param.get('type', '')}, {req}): {param.get('description', '')}"
        )
    lines.append("")


def _append_returns(lines: list[str], doc: dict[str, Any], *, compact: bool = False) -> None:
    returns = doc.get("returns", {})
    if not returns:
        return
    rtype = returns.get("type", "")
    rdesc = returns.get("description", "")
    if compact:
        lines.extend([f"Returns: {rtype} - {rdesc}", ""])
    else:
        lines.extend(["## Returns", f"**`{rtype}`**: {rdesc}", ""])


def _append_examples(lines: list[str], doc: dict[str, Any], *, first_only: bool = False) -> None:
    examples = doc.get("examples", [])
    if not examples:
        return
    selected = examples[:1] if first_only else examples
    lines.append("Example:" if first_only else "## Examples")
    for i, example in enumerate(selected, 1):
        if not first_only:
            lines.append(f"### Example {i}: {example.get('description', '')}")
        lines.extend(["```python", example.get("code", ""), "```", ""])


def _append_list_section(
    lines: list[str],
    title: str,
    values: Any,
    *,
    bullet: bool = False,
    compact: bool = False,
) -> None:
    if not values:
        return
    lines.append(f"{title}:" if compact else f"## {title}")
    if isinstance(values, list):
        for value in values:
            lines.append(f"- {value}" if bullet or compact else str(value))
    else:
        lines.append(str(values))
    lines.append("")
