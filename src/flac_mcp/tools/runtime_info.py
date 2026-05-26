"""Runtime environment inspection tool for the connected FLAC bridge."""

import json
from typing import Any

from fastmcp import FastMCP

from flac_mcp.bridge import get_bridge_client
from flac_mcp.contracts import build_ok
from flac_mcp.formatting import build_bridge_error, build_operation_error, is_bridge_connectivity_error

_RUNTIME_INFO_CODE = r"""
import json
import platform
import re
import sys

import itasca as it

executable = getattr(sys, "executable", "") or ""
exe_lower = executable.lower()

product = "unknown"
if "flac3d" in exe_lower or "flac3" in exe_lower:
    product = "flac3d"
elif "flac2d" in exe_lower or "flac2" in exe_lower:
    product = "flac2d"

version = None
match = re.search(r"(?:flac(?:2d|3d)?|itascasoftware)(\d)(\d{2})", exe_lower)
if match:
    version = "%s.%s" % (match.group(1), match.group(2).lstrip("0") or "0")
else:
    match = re.search(r"flac(?:2d|3d)?(?P<major>[679])(?:[_\-.]|$)", exe_lower)
    if match:
        version = "%s.0" % match.group("major")

try:
    dim = it.dim()
except Exception as exc:
    dim = None
    dim_error = str(exc)
else:
    dim_error = None

if dim == 2 and product == "unknown":
    product = "flac2d"
elif dim == 3 and product == "unknown":
    product = "flac3d"

result = {
    "product": product,
    "dimension": dim,
    "flac_version": version,
    "python_version": sys.version.split()[0],
    "python_executable": executable,
    "platform": platform.platform(),
}
if dim_error:
    result["dimension_error"] = dim_error

print(json.dumps(result, sort_keys=True))
"""


def register(mcp: FastMCP) -> None:
    """Register flac_get_runtime_info tool."""

    @mcp.tool()
    async def flac_get_runtime_info() -> dict[str, Any]:
        """Inspect the FLAC process connected through the bridge.

        Returns the detected FLAC product, model dimension, inferred FLAC
        version, embedded Python version, and executable path. This should be
        used before dimension- or version-sensitive workflows.
        """
        try:
            client = await get_bridge_client()
            response = await client.execute_code(_RUNTIME_INFO_CODE, timeout_ms=10000)
        except Exception as exc:
            if is_bridge_connectivity_error(exc):
                return build_bridge_error(exc)
            return build_operation_error("runtime_info_failed", "Runtime inspection failed", reason=str(exc))

        if response.get("status") not in {"success", "completed", "ok"}:
            return build_operation_error(
                str(response.get("status") or "runtime_info_failed"),
                "Runtime inspection failed",
                reason=str(response.get("message") or ""),
                output=((response.get("data") or {}).get("output")) or None,
            )

        data = response.get("data") or {}
        result = data.get("result")
        if isinstance(result, dict):
            return build_ok(result)

        output = data.get("output") or ""
        try:
            parsed = json.loads(output.strip().splitlines()[-1])
        except Exception as exc:
            return build_operation_error(
                "runtime_info_parse_failed",
                "Runtime inspection returned an unrecognized payload",
                reason=str(exc),
                output=output or None,
            )

        if not isinstance(parsed, dict):
            return build_operation_error(
                "runtime_info_parse_failed",
                "Runtime inspection returned a non-object payload",
                output=output or None,
            )

        return build_ok(parsed)
