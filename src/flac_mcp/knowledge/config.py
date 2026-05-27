"""PFC Documentation path configuration.

Defines paths for static documentation resources bundled with pfc-mcp.
All paths are resolved relative to this package's resources/ directory.
"""

from pathlib import Path

# Base path for all documentation resources
_RESOURCES_DIR = Path(__file__).parent / "resources"

# Static source documentation (version-controlled, JSON format)
# Contains PFC Python SDK API documentation exported from official docs
PFC_DOCS_SOURCE = _RESOURCES_DIR / "python_sdk_docs"

# Command documentation root (version-controlled, JSON format)
# Contains versioned PFC command documentation and command index metadata
PFC_COMMAND_DOCS_ROOT = _RESOURCES_DIR / "command_docs"

# Reference documentation (version-controlled, JSON format)
# Syntax elements used within commands: contact models, range elements, etc.
PFC_REFERENCES_ROOT = _RESOURCES_DIR / "references"

# Maximum number of API matches to return from keyword search
SDK_SEARCH_TOP_N = 3
