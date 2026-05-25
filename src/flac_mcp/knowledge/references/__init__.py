"""FLAC Reference Documentation System.

This module provides reference documentation loading and formatting capabilities
for FLAC reference items (zone models, range elements).

Components:
    - ReferenceLoader: Load reference docs from JSON files
    - ReferenceFormatter: Format reference documentation as markdown
"""

from flac_mcp.knowledge.references.formatter import ReferenceFormatter
from flac_mcp.knowledge.references.loader import ReferenceLoader

__all__ = [
    "ReferenceLoader",
    "ReferenceFormatter",
]
