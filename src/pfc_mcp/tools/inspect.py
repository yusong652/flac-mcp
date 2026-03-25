"""PFC inspect tool — synchronous REPL for querying model state."""

from typing import Any

from fastmcp import FastMCP

from pfc_mcp.bridge import get_bridge_client
from pfc_mcp.contracts import build_ok
from pfc_mcp.formatting import build_bridge_error, build_operation_error, is_bridge_connectivity_error
from pfc_mcp.utils import ConsoleCode, ConsoleTimeoutSeconds


def register(mcp: FastMCP) -> None:
    """Register pfc_inspect tool."""

    @mcp.tool()
    async def pfc_inspect(
        code: ConsoleCode,
        timeout: ConsoleTimeoutSeconds = 10,
    ) -> dict[str, Any]:
        """Execute a Python snippet directly in the running PFC process.

        Code executes synchronously in the PFC main thread during the
        cycle. Consider side effects carefully — any state changes
        (variable assignments, model modifications) persist in the
        process. For long-running or simulation-advancing operations,
        prefer pfc_execute_task.

        Keep snippets short and focused; a strict timeout applies.
        """
        try:
            client = await get_bridge_client()
            response = await client.inspect_execute(
                code=code,
                timeout_ms=timeout * 1000,
            )
        except Exception as exc:
            if is_bridge_connectivity_error(exc):
                return build_bridge_error(exc)
            return build_operation_error(
                "inspect_failed",
                "Inspect execution failed",
                reason=str(exc),
            )

        status = response.get("status", "unknown")
        message = response.get("message", "")

        if status == "timeout":
            return build_operation_error(
                "timeout",
                "Inspect timed out",
                reason=message,
                action="Reduce code complexity or increase timeout",
            )

        if status == "error":
            error = response.get("error") or {}
            return build_operation_error(
                error.get("code", "inspect_error"),
                error.get("message", message),
                reason=message,
            )

        data = response.get("data") or {}
        result_data: dict[str, Any] = {
            "output": data.get("output") or "(no output)",
        }
        if data.get("result") is not None:
            result_data["result"] = data["result"]

        return build_ok(result_data)
