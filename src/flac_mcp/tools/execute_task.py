"""FLAC task execution tool backed by itasca-mcp-bridge."""

import uuid
from typing import Any

from fastmcp import FastMCP

from flac_mcp.bridge import get_bridge_client
from flac_mcp.contracts import build_ok
from flac_mcp.formatting import build_bridge_error, build_operation_error
from flac_mcp.utils import ScriptPath, TaskDescription


def register(mcp: FastMCP) -> None:
    """Register flac_execute_task tool."""

    @mcp.tool()
    async def flac_execute_task(
        entry_script: ScriptPath,
        description: TaskDescription,
    ) -> dict[str, Any]:
        """Submit a Python script file for asynchronous execution in FLAC.

        Returns a task_id immediately; the script runs in the background.
        Use the companion tools to manage the task lifecycle:
        - flac_check_task_status: poll output, progress, and final status
        - flac_interrupt_task: cancel a running task
        - flac_list_tasks: browse task history

        While the task is cycling, you can call flac_execute_code at any
        time to inspect or modify simulation state — including variables
        the task depends on. This is the standard way to probe progress,
        tune parameters mid-run, swap callbacks, or trigger early
        termination via a sentinel variable. Both tools share the same
        __main__ namespace in FLAC's main thread.

        Console output from itasca.command() inside the script —
        table dumps, list output, command summaries — is captured
        and interleaved with Python prints in the task log, visible
        through flac_check_task_status.

        This is the async / background execution path: pollable via
        flac_check_task_status, cancellable via flac_interrupt_task.
        Submission does not lock parameters — start with reasonable
        values and refine live via flac_execute_code as the task
        cycles. For synchronous, inline execution, use
        flac_execute_code directly.

        Submission uses the bridge's `execute_task` protocol message. If
        a submission times out, the connected bridge may predate it —
        confirm its version with flac_execute_code (`import
        itasca_mcp_bridge; print(itasca_mcp_bridge.__version__)`). To
        upgrade, fetch and follow the bootstrap guide, then resubmit:
        https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap.md
        """
        try:
            client = await get_bridge_client()
        except Exception as exc:
            # Connection failed — no task_id generated, nothing to track
            return build_bridge_error(exc)

        task_id = uuid.uuid4().hex[:6]

        try:
            response = await client.execute_task(
                script_path=entry_script,
                description=description,
                task_id=task_id,
            )
        except Exception as exc:
            # Connected but request failed — task may or may not exist on bridge
            return build_bridge_error(exc, task_id=task_id)

        status = response.get("status", "unknown")
        message = response.get("message", "")

        if status != "pending":
            return build_operation_error(
                status or "submission_failed",
                message or "Task submission rejected by bridge",
                task_id=task_id,
                action="Check script path and bridge logs, then retry",
            )

        return build_ok(
            {
                "task_id": task_id,
                "entry_script": entry_script,
                "description": description,
                "task_status": "pending",
                "message": message or "submitted",
            }
        )
