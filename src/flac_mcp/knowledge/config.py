"""FLAC documentation path configuration.

Defines paths for static documentation resources bundled with flac-mcp.
All paths are resolved relative to this package's resources/ directory.
"""

from pathlib import Path

# Base path for all documentation resources
_RESOURCES_DIR = Path(__file__).parent / "resources"

# Static source documentation (version-controlled, JSON format)
# Contains FLAC/Itasca Python SDK API documentation exported from official docs
FLAC_DOCS_SOURCE = _RESOURCES_DIR / "python_sdk_docs"

# Command documentation root (version-controlled, JSON format)
# Contains versioned FLAC command documentation and command index metadata
FLAC_COMMAND_DOCS_ROOT = _RESOURCES_DIR / "command_docs"

# Reference documentation (version-controlled, JSON format)
# Syntax elements used within commands: zone models, range elements, etc.
FLAC_REFERENCES_ROOT = _RESOURCES_DIR / "references"

# Maximum number of API matches to return from keyword search
SDK_SEARCH_TOP_N = 3
