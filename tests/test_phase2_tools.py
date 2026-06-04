import asyncio

from flac_mcp.formatting import build_bridge_error
from flac_mcp.server import mcp
from flac_mcp.tools.task_formatting import paginate_output
from flac_mcp.utils import validate_script_path


def test_phase2_tools_registered() -> None:
    tools = asyncio.run(mcp._tool_manager.get_tools())
    expected = {
        "flac_execute_task",
        "flac_check_task_status",
        "flac_list_tasks",
        "flac_interrupt_task",
    }
    assert expected.issubset(set(tools.keys()))
    assert "flac_execute_code" in tools


def test_pagination() -> None:
    text, page = paginate_output(
        output="a\nb\nc\nd",
        skip_newest=0,
        limit=2,
        filter_text=None,
    )

    assert text == "c\nd"
    assert page["line_range"] == "3-4"
    assert page["total_lines"] == 4


def test_validate_script_path_requires_absolute() -> None:
    assert validate_script_path("/tmp/run.py") == "/tmp/run.py"

    try:
        validate_script_path("relative/run.py")
    except ValueError as exc:
        assert "absolute path" in str(exc)
    else:
        raise AssertionError("relative path should raise ValueError")


def test_bridge_error_message_is_friendly() -> None:
    err = OSError("Multiple exceptions: [Errno 61] Connect call failed")
    envelope = build_bridge_error(err)

    assert envelope["ok"] is False
    error = envelope["error"]
    assert error["code"] == "bridge_unavailable"
    assert error["message"] == "FLAC3D bridge unavailable"
    assert error["details"]["reason"] == "cannot connect to bridge service"
    assert error["details"]["action"] == "start itasca-mcp-bridge in FLAC3D, then retry"
