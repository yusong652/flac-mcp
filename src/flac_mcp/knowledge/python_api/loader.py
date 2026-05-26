"""Data loading layer for FLAC SDK documentation.

This module is responsible for loading documentation data from JSON files
and providing cached access to avoid repeated I/O operations.

Responsibilities:
- Load index.json (quick reference and metadata)
- Load keywords.json files (from all modules)
- Load individual API documentation files
- Cache loaded data for performance
"""

import json
from collections import defaultdict
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

from flac_mcp.knowledge.compatibility import FLACProduct, normalize_product
from flac_mcp.knowledge.config import FLAC_DOCS_SOURCE
from flac_mcp.knowledge.python_api.product_index import (
    annotate_api_doc,
    is_api_available,
    normalize_api_version,
    source_info,
    versioned_docs_dir,
)


class DocumentationLoader:
    """Loads and caches SDK documentation data.

    This class provides static methods for loading various documentation
    resources. All methods use caching to avoid repeated file I/O.
    """

    @staticmethod
    def _docs_dir(product: str, version: str) -> Path:
        """Return the docs directory for a product/version API snapshot."""
        versioned = versioned_docs_dir(product, version)
        if versioned.exists():
            return versioned
        return FLAC_DOCS_SOURCE

    @staticmethod
    @lru_cache(maxsize=8)
    def _load_base_index(docs_dir: str) -> dict[str, Any]:
        """Load the unfiltered main index file with caching."""
        docs_path = Path(docs_dir)
        index_path = docs_path / "index.json"
        if not index_path.exists():
            raise FileNotFoundError(f"Index file not found: {index_path}")

        with open(index_path, encoding="utf-8") as f:
            index = json.load(f)

        return DocumentationLoader._expand_object_methods(index)

    @staticmethod
    @lru_cache(maxsize=32)
    def load_index(
        product: str | FLACProduct | None = FLACProduct.ANY.value, version: str | None = "9.0"
    ) -> dict[str, Any]:
        """Load a product/version-scoped Python API index.

        The index file contains:
        - quick_ref: Direct API name to file reference mapping
        - keywords: Keyword to API list mapping (if present)
        - fallback_hints: Suggestions when SDK doesn't support operation

        Returns:
            Dict containing index data structure

        Raises:
            FileNotFoundError: If index.json doesn't exist

        Example:
            >>> index = DocumentationLoader.load_index()
            >>> quick_ref = index["quick_ref"]
            >>> "itasca.zone.list" in quick_ref
            True
        """
        product_value = normalize_product(product)
        version_value = normalize_api_version(version)
        docs_dir = DocumentationLoader._docs_dir(product_value, version_value)
        base_index = deepcopy(DocumentationLoader._load_base_index(str(docs_dir)))
        base_index["_docs_dir"] = str(docs_dir)
        if product_value == FLACProduct.ANY.value:
            base_index["product"] = product_value
            base_index["version"] = version_value
            base_index["source"] = source_info(product_value, version_value)
            return base_index
        return DocumentationLoader._build_product_index(base_index, product_value, version_value)

    @staticmethod
    def _build_product_index(index: dict[str, Any], product: str, version: str) -> dict[str, Any]:
        """Build a product/version API index before browse/search sees it."""
        source = source_info(product, version)
        index["product"] = product
        index["version"] = version
        index["source"] = source

        if not source.get("applicable") or not source.get("bundled"):
            index["modules"] = {}
            index["objects"] = {}
            index["quick_ref"] = {}
            return index

        quick_ref = index.get("quick_ref", {})
        allowed_quick_ref: dict[str, str] = {}
        for api_name, file_ref in quick_ref.items():
            docs_dir = Path(str(index.get("_docs_dir", FLAC_DOCS_SOURCE)))
            api_doc = DocumentationLoader._load_api_doc_from_ref(file_ref, docs_dir)
            if api_doc and is_api_available(api_name, api_doc, product, version):
                allowed_quick_ref[api_name] = file_ref

        index["quick_ref"] = allowed_quick_ref
        index["modules"] = DocumentationLoader._filter_modules(index.get("modules", {}), allowed_quick_ref)
        index["objects"] = DocumentationLoader._filter_objects(index.get("objects", {}), allowed_quick_ref)
        return index

    @staticmethod
    def _filter_modules(modules: dict[str, Any], quick_ref: dict[str, str]) -> dict[str, Any]:
        filtered: dict[str, Any] = {}
        for module_key, module_info in modules.items():
            full_prefix = "itasca" if module_key == "itasca" else f"itasca.{module_key}"
            functions = module_info.get("functions", [])
            function_names = [
                str(func.get("name") if isinstance(func, dict) else func)
                for func in functions
                if f"{full_prefix}.{func.get('name') if isinstance(func, dict) else func}" in quick_ref
            ]
            if function_names or module_key == "vec":
                filtered[module_key] = {**module_info, "functions": function_names}
        return filtered

    @staticmethod
    def _filter_objects(objects: dict[str, Any], quick_ref: dict[str, str]) -> dict[str, Any]:
        filtered: dict[str, Any] = {}
        for object_name, object_info in objects.items():
            file_path = object_info.get("file", "")
            if not file_path:
                continue
            allowed_methods = sorted(
                api_name.rsplit(".", 1)[-1]
                for api_name, file_ref in quick_ref.items()
                if file_ref.startswith(f"{file_path}#")
            )
            if not allowed_methods:
                continue
            entry = {**object_info}
            method_groups = object_info.get("method_groups", {})
            if isinstance(method_groups, dict):
                entry["method_groups"] = DocumentationLoader._filter_method_groups(method_groups, set(allowed_methods))
            filtered[object_name] = entry
        return filtered

    @staticmethod
    def _filter_method_groups(method_groups: dict[str, Any], allowed_methods: set[str]) -> dict[str, Any]:
        filtered: dict[str, Any] = {}
        for group, methods in method_groups.items():
            if isinstance(methods, str):
                names = [name.strip() for name in methods.split(",")]
            elif isinstance(methods, list):
                names = [str(name) for name in methods]
            else:
                continue
            kept = [name for name in names if name in allowed_methods]
            if kept:
                filtered[group] = kept
        return filtered

    @staticmethod
    @lru_cache(maxsize=32)
    def load_all_keywords(
        product: str | FLACProduct | None = FLACProduct.ANY.value,
        version: str | None = "9.0",
    ) -> dict[str, list[str]]:
        """Load keywords from all modules with caching and merging.

        Aggregates keywords from:
        - itasca_keywords.json (top-level module)
        - modules/**/keywords.json (all modules and submodules recursively)

        Uses merge strategy: when multiple modules define the same keyword,
        all associated APIs are collected (not overwritten).

        Returns:
            Dict mapping keywords to list of API names

        Example:
            >>> keywords = DocumentationLoader.load_all_keywords()
            >>> keywords["zone stress"]
            ["itasca.zone.Zone.stress"]
        """
        # Use defaultdict to automatically handle merging
        all_keywords: defaultdict[str, list[str]] = defaultdict(list)

        # Load itasca top-level keywords
        product_value = normalize_product(product)
        version_value = normalize_api_version(version)
        docs_dir = DocumentationLoader._docs_dir(product_value, version_value)

        itasca_keywords_path = docs_dir / "itasca_keywords.json"
        if itasca_keywords_path.exists():
            with open(itasca_keywords_path, encoding="utf-8") as f:
                data = json.load(f)
                DocumentationLoader._merge_keywords(all_keywords, data.get("keywords", {}))

        # Load keywords from all sub-modules (recursive)
        modules_dir = docs_dir / "modules"
        if modules_dir.exists():
            DocumentationLoader._load_keywords_recursive(modules_dir, all_keywords)

        product_index = DocumentationLoader.load_index(product_value, version_value)
        allowed_apis = set(product_index.get("quick_ref", {}))

        filtered_keywords: dict[str, list[str]] = {}
        for keyword, api_names in all_keywords.items():
            kept = [api_name for api_name in api_names if api_name in allowed_apis]
            if kept:
                filtered_keywords[keyword] = kept

        return filtered_keywords

    @staticmethod
    def load_api_doc(
        api_name: str,
        product: str | FLACProduct | None = FLACProduct.ANY.value,
        version: str | None = "9.0",
    ) -> dict[str, Any] | None:
        """Load documentation for a specific API or module.

        Args:
            api_name: Full API name like "itasca.zone.list" or "Zone.stress"
                     or module name like "itasca.zone"

        Returns:
            API documentation dict with fields:

            For functions/methods:
                - signature: Function signature
                - description: Detailed description
                - parameters: List of parameter definitions
                - returns: Return value information
                - examples: Usage examples
                - limitations: Known limitations (optional)
                - fallback_commands: Alternative commands (optional)
                - best_practices: Recommended practices (optional)
                - notes: Additional notes (optional)
                - see_also: Related APIs (optional)

            For modules:
                - type: "module"
                - signature: Module signature with function count
                - description: Module description
                - available_functions: List of all function names in the module
                - usage_note: Guidance on querying specific functions

            Returns None if API not found.

        Example:
            >>> doc = DocumentationLoader.load_api_doc("itasca.zone.list")
            >>> doc["signature"]
            "itasca.zone.list() -> tuple of Zone objects."

            >>> doc = DocumentationLoader.load_api_doc("itasca.zone")
            >>> doc["type"]
            "module"
        """
        product_value = normalize_product(product)
        version_value = normalize_api_version(version)
        index = DocumentationLoader.load_index(product_value, version_value)

        # Try 1: Get file reference from quick_ref (functions/methods)
        ref = index["quick_ref"].get(api_name)
        if not ref:
            # Try 2: Check if it's a module name
            module_doc = DocumentationLoader._load_module_doc(api_name, index, product_value, version_value)
            if module_doc:
                return module_doc
            # Not found in either quick_ref or modules
            return None

        docs_dir = Path(str(index.get("_docs_dir", FLAC_DOCS_SOURCE)))
        doc = DocumentationLoader._load_api_doc_from_ref(ref, docs_dir)
        if doc:
            return annotate_api_doc(api_name, doc, product_value, version_value)
        return None

    @staticmethod
    def _load_api_doc_from_ref(ref: str, docs_dir: Path) -> dict[str, Any] | None:
        """Load an API documentation entry from a quick_ref file reference."""
        # Parse file path and anchor
        # Format: "file_name.json#function_name"
        file_name, anchor = ref.split("#")
        doc_path = docs_dir / file_name

        if not doc_path.exists():
            return None

        with open(doc_path, encoding="utf-8") as f:
            doc = json.load(f)

        # Find the specific function or method
        # Object method files contain "methods" key
        # Module function files contain "functions" key
        if "methods" in doc:
            for method in doc["methods"]:
                if method["name"] == anchor:
                    return cast(dict[str, Any], method)
        elif "functions" in doc:
            for func in doc["functions"]:
                if func["name"] == anchor:
                    return cast(dict[str, Any], func)

        return None

    @staticmethod
    def _expand_object_methods(index: dict[str, Any]) -> dict[str, Any]:
        """Expand object method entries to full official paths.

        Object methods like "Zone.stress" are stored in index as short paths.
        This method expands them to full official paths like
        "itasca.zone.Zone.stress", eliminating the need for runtime path resolution.

        Args:
            index: Loaded index dictionary

        Returns:
            Modified index with expanded object method entries

        Example:
            Input quick_ref:
                "Zone.stress": "modules/zone/Zone.json#stress"

            Output quick_ref:
                "itasca.zone.Zone.stress": "modules/zone/Zone.json#stress"
        """
        from flac_mcp.knowledge.python_api.types.mappings import CLASS_TO_MODULE

        quick_ref = index.get("quick_ref", {})

        # Find all object method entries (Class.method format, not starting with itasca.)
        object_methods = {}
        entries_to_remove = []

        for api_name, file_ref in quick_ref.items():
            # Skip if already full path or module function
            if api_name.startswith("itasca."):
                continue

            # Check if it's an object method (Class.method format)
            if "." in api_name:
                class_name = api_name.split(".")[0]
                # Check if it's a known class with module mapping
                if class_name in CLASS_TO_MODULE:
                    object_methods[api_name] = file_ref
                    entries_to_remove.append(api_name)

        # Expand each object method to full path
        for short_path, file_ref in object_methods.items():
            class_name = short_path.split(".")[0]
            module_name = CLASS_TO_MODULE[class_name]
            # Create full official path: Zone.vel → itasca.zone.Zone.vel
            full_path = f"itasca.{module_name}.{short_path}"
            quick_ref[full_path] = file_ref

        # Remove original short path entries
        for api_name in entries_to_remove:
            del quick_ref[api_name]

        return index

    @staticmethod
    def _load_module_doc(
        api_name: str,
        index: dict[str, Any],
        product: str,
        version: str,
    ) -> dict[str, Any] | None:
        """Load module-level documentation.

        Args:
            api_name: API name that might be a module (e.g., "itasca.zone", "itasca.gridpoint")
            index: Loaded index dictionary

        Returns:
            Module documentation dict or None if not a module

        Example:
            Input: "itasca.zone"
            Output: {
                "type": "module",
                "signature": "itasca.zone (module - 20 functions available)",
                "description": "Zone object management...",
                "available_functions": ["itasca.zone.list", ...]
            }
        """
        modules = index.get("modules", {})

        # Extract module name from API name
        # "itasca.zone" -> "zone"
        # "itasca.gridpoint" -> "gridpoint"
        if not api_name.startswith("itasca."):
            return None

        module_name = api_name.replace("itasca.", "", 1)

        # Check if this module exists
        if module_name not in modules:
            return None

        module_info = modules[module_name]

        # Build list of available functions with full paths
        functions = module_info.get("functions", [])
        available_functions = [f"itasca.{module_name}.{func}" for func in functions]

        func_count = len(functions)

        return {
            "type": "module",
            "signature": f"{api_name} (module - {func_count} function{'s' if func_count != 1 else ''} available)",
            "description": module_info.get("description", f"{module_name} module"),
            "available_functions": available_functions,
            "availability": {
                "products": (
                    [product]
                    if product != FLACProduct.ANY.value
                    else [FLACProduct.FLAC2D.value, FLACProduct.FLAC3D.value]
                ),
                "version": version,
                "source": source_info(product, version),
            },
            "usage_note": (
                f"Query specific functions (e.g., '{available_functions[0] if available_functions else 'function_name'}') "
                "for detailed documentation including parameters, return types, and examples."
            ),
        }

    @staticmethod
    def _merge_keywords(target: defaultdict[str, list[str]], source: dict[str, list[str]]) -> None:
        """Merge keywords from source into target without overwriting.

        When a keyword exists in both target and source, their API lists
        are merged (deduplicated).

        Args:
            target: Target defaultdict to merge into
            source: Source dict to merge from
        """
        for keyword, apis in source.items():
            # Skip comment entries
            if keyword.startswith("_comment"):
                continue

            # Extend the list (merge, don't replace)
            target[keyword].extend(apis)

            # Deduplicate while preserving order
            target[keyword] = list(dict.fromkeys(target[keyword]))

    @staticmethod
    def _load_keywords_recursive(directory: Path, all_keywords: defaultdict[str, list[str]]) -> None:
        """Recursively load keywords from a directory tree.

        Scans the given directory and all subdirectories for keywords.json files
        and merges them into all_keywords.

        Args:
            directory: Directory to scan
            all_keywords: Target defaultdict to accumulate keywords
        """
        for item in directory.iterdir():
            if item.is_dir():
                # Load keywords.json in this directory if it exists
                keywords_file = item / "keywords.json"
                if keywords_file.exists():
                    with open(keywords_file, encoding="utf-8") as f:
                        data = json.load(f)
                        DocumentationLoader._merge_keywords(all_keywords, data.get("keywords", {}))

                # Recursively process subdirectories
                DocumentationLoader._load_keywords_recursive(item, all_keywords)

    @staticmethod
    def load_module(
        module_key: str,
        product: str | FLACProduct | None = FLACProduct.ANY.value,
        version: str | None = "9.0",
    ) -> dict[str, Any] | None:
        """Load module documentation by index key.

        Args:
            module_key: Module key from index (e.g., "itasca", "zone", "gridpoint.facet")

        Returns:
            Module documentation dict with:
                - module: Module name
                - description: Module description
                - functions: List of function definitions

            Returns None if module not found.

        Example:
            >>> doc = DocumentationLoader.load_module("zone")
            >>> doc["module"]
            "itasca.zone"
            >>> len(doc["functions"])
            9
        """
        product_value = normalize_product(product)
        version_value = normalize_api_version(version)
        index = DocumentationLoader.load_index(product_value, version_value)
        modules = index.get("modules", {})

        if module_key not in modules:
            return None

        module_info = modules[module_key]
        file_path = module_info.get("file")

        if not file_path:
            # Return basic info from index if no file specified
            return {
                "module": f"itasca.{module_key}" if module_key != "itasca" else "itasca",
                "description": module_info.get("description", ""),
                "functions": module_info.get("functions", []),
                "availability": {"product": product_value, "version": version_value, "source": index.get("source", {})},
            }

        # Load full module documentation
        docs_dir = Path(str(index.get("_docs_dir", FLAC_DOCS_SOURCE)))
        doc_path = docs_dir / file_path
        if not doc_path.exists():
            # Return basic info from index
            return {
                "module": f"itasca.{module_key}" if module_key != "itasca" else "itasca",
                "description": module_info.get("description", ""),
                "functions": module_info.get("functions", []),
                "availability": {"product": product_value, "version": version_value, "source": index.get("source", {})},
            }

        with open(doc_path, encoding="utf-8") as f:
            doc = cast(dict[str, Any], json.load(f))

        allowed_names = set(module_info.get("functions", []))
        module_prefix = "itasca" if module_key == "itasca" else f"itasca.{module_key}"
        functions = doc.get("functions", [])
        if isinstance(functions, list):
            doc["functions"] = [
                annotate_api_doc(
                    f"{module_prefix}.{func['name']}",
                    func,
                    product_value,
                    version_value,
                )
                for func in functions
                if isinstance(func, dict) and func.get("name") in allowed_names
            ]
        doc["availability"] = {"product": product_value, "version": version_value, "source": index.get("source", {})}
        return doc

    @staticmethod
    def load_function(
        module_key: str,
        func_name: str,
        product: str | FLACProduct | None = FLACProduct.ANY.value,
        version: str | None = "9.0",
    ) -> dict[str, Any] | None:
        """Load function documentation from a module.

        Args:
            module_key: Module key from index (e.g., "itasca", "zone")
            func_name: Function name (e.g., "create", "cycle")

        Returns:
            Function documentation dict with:
                - name: Function name
                - signature: Function signature
                - description: Detailed description
                - parameters: List of parameter definitions
                - returns: Return value information
                - examples: Usage examples (optional)

            Returns None if function not found.

        Example:
            >>> doc = DocumentationLoader.load_function("zone", "create")
            >>> doc["signature"]
            "itasca.zone.create(radius: float, centroid: vec, id: int = None) -> Zone"
        """
        module_doc = DocumentationLoader.load_module(module_key, product, version)
        if not module_doc:
            return None

        functions = module_doc.get("functions", [])
        for func in functions:
            if isinstance(func, dict) and func.get("name") == func_name:
                return func

        return None

    @staticmethod
    def load_object(
        object_name: str,
        product: str | FLACProduct | None = FLACProduct.ANY.value,
        version: str | None = "9.0",
    ) -> dict[str, Any] | None:
        """Load object documentation by class name.

        Args:
            object_name: Object class name (e.g., "Zone", "Contact", "Gridpoint")

        Returns:
            Object documentation dict with:
                - class: Class name
                - description: Object description
                - note: Usage note (optional)
                - method_groups: Dict of method group names to method lists
                - methods: List of method definitions (if full doc available)

            Returns None if object not found.

        Example:
            >>> doc = DocumentationLoader.load_object("Zone")
            >>> doc["class"]
            "Zone"
            >>> "position" in doc["method_groups"]
            True
        """
        product_value = normalize_product(product)
        version_value = normalize_api_version(version)
        index = DocumentationLoader.load_index(product_value, version_value)
        objects = index.get("objects", {})

        if object_name not in objects:
            return None

        object_info = objects[object_name]
        file_path = object_info.get("file")

        if not file_path:
            # Return basic info from index
            return cast(dict[str, Any], object_info)

        # Load full object documentation
        docs_dir = Path(str(index.get("_docs_dir", FLAC_DOCS_SOURCE)))
        doc_path = docs_dir / file_path
        if not doc_path.exists():
            return cast(dict[str, Any], object_info)

        with open(doc_path, encoding="utf-8") as f:
            doc = cast(dict[str, Any], json.load(f))

        allowed_names = DocumentationLoader._method_names_from_groups(object_info.get("method_groups", {}))
        quick_ref = index.get("quick_ref", {})
        methods = doc.get("methods", [])
        if isinstance(methods, list):
            filtered_methods = []
            for method in methods:
                if not isinstance(method, dict) or method.get("name") not in allowed_names:
                    continue
                api_path = DocumentationLoader._api_name_for_ref(
                    quick_ref,
                    f"{file_path}#{method['name']}",
                )
                filtered_methods.append(
                    annotate_api_doc(api_path or method["name"], method, product_value, version_value)
                )
            doc["methods"] = filtered_methods
        doc["method_groups"] = object_info.get("method_groups", {})
        doc["availability"] = {"product": product_value, "version": version_value, "source": index.get("source", {})}
        return doc

    @staticmethod
    def _method_names_from_groups(method_groups: Any) -> set[str]:
        names: set[str] = set()
        if not isinstance(method_groups, dict):
            return names
        for methods in method_groups.values():
            if isinstance(methods, str):
                names.update(name.strip() for name in methods.split(",") if name.strip())
            elif isinstance(methods, list):
                names.update(str(name) for name in methods)
        return names

    @staticmethod
    def _api_name_for_ref(quick_ref: dict[str, str], expected_ref: str) -> str | None:
        for api_name, file_ref in quick_ref.items():
            if file_ref == expected_ref:
                return api_name
        return None

    @staticmethod
    def load_method(
        object_name: str,
        method_name: str,
        product: str | FLACProduct | None = FLACProduct.ANY.value,
        version: str | None = "9.0",
    ) -> dict[str, Any] | None:
        """Load method documentation from an object.

        Args:
            object_name: Object class name (e.g., "Zone", "Gridpoint")
            method_name: Method name (e.g., "pos", "vel")

        Returns:
            Method documentation dict with:
                - name: Method name
                - signature: Method signature
                - description: Detailed description
                - parameters: List of parameter definitions (optional)
                - returns: Return value information

            Returns None if method not found.

        Example:
            >>> doc = DocumentationLoader.load_method("Zone", "pos")
            >>> doc["signature"]
            "zone.pos() -> vec"
        """
        object_doc = DocumentationLoader.load_object(object_name, product, version)
        if not object_doc:
            return None

        methods = object_doc.get("methods", [])
        for method in methods:
            if isinstance(method, dict) and method.get("name") == method_name:
                return method

        return None

    @staticmethod
    def clear_cache() -> None:
        """Clear all cached data.

        Useful for testing or when documentation files are updated.
        """
        DocumentationLoader._load_base_index.cache_clear()
        DocumentationLoader.load_index.cache_clear()
        DocumentationLoader.load_all_keywords.cache_clear()
