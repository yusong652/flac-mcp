"""flac-mcp bridge add-on — install/upgrade + start, in one step.

Run this *inside FLAC's embedded Python* (FLAC GUI IPython console, or
open/execute the file from the FLAC GUI). It is the "Option A" entry point
referenced by the README and the bootstrap guide: it installs or upgrades
the ``itasca-mcp-bridge`` package from PyPI and then starts the bridge
WebSocket server so MCP clients can reach this FLAC process.

Safe to re-run every session (daily startup): if PyPI is unreachable but a
working copy is already installed, it skips the upgrade and starts anyway.

Notes
-----
* FLAC's ``sys.executable`` is the GUI binary, not a Python interpreter, so
  ``python -m pip`` does not work here — pip is driven in-process via its
  internal entry point (matching the bridge's own documented install path).
* ``websockets`` is pulled in automatically with a version matched to the
  embedded Python (9.1 on Python 3.6, 16.0 on Python 3.10) via the package's
  dependency markers — no manual pin needed.
* Python 3.6+ compatible (FLAC 6/7 embed 3.6, FLAC 9 embeds 3.10).
"""

import importlib
import os
import sys

PACKAGE = "itasca-mcp-bridge"
MODULE = "itasca_mcp_bridge"


def _resolve_pip_main():
    """Return pip's in-process ``main`` across the pip versions FLAC ships."""
    for path in (
        "pip._internal.cli.main",  # pip >= 19.3
        "pip._internal.main",  # pip 19.0 - 19.2
        "pip._internal",  # pip < 19.0
        "pip",  # very old pip
    ):
        try:
            module = importlib.import_module(path)
        except ImportError:
            continue
        main = getattr(module, "main", None)
        if callable(main):
            return main
    return None


def _ensure_installed():
    """Install or upgrade the bridge; tolerate offline if already present."""
    pip_main = _resolve_pip_main()
    if pip_main is None:
        print("[addon] pip not available in FLAC Python; skipping install, trying an already-installed copy.")
        return
    print(f"[addon] Installing/upgrading {PACKAGE} from PyPI ...")
    try:
        code = pip_main(["install", "--user", "--upgrade", PACKAGE])
    except SystemExit as exc:  # some pip versions raise instead of return
        code = exc.code
    except Exception as exc:  # noqa: BLE001 - network/permission/etc.
        print(f"[addon] Install step failed ({exc}); will try an already-installed copy.")
        return
    if code:
        print(f"[addon] pip exited with {code!r}; will try an already-installed copy (offline daily restart is fine).")


def _import_bridge():
    """Import the bridge, refreshing caches so a fresh install is visible."""
    importlib.invalidate_caches()
    try:
        import site

        user_site = site.getusersitepackages()
        if user_site and user_site not in sys.path:
            sys.path.append(user_site)
    except Exception:  # noqa: BLE001 - site can be unusual in embedded Python
        pass
    if MODULE in sys.modules:
        return importlib.reload(sys.modules[MODULE])
    return importlib.import_module(MODULE)


def main():
    _ensure_installed()
    try:
        bridge = _import_bridge()
    except ImportError as exc:
        raise SystemExit(
            f"[addon] Could not import {MODULE} after install ({exc}).\n"
            "        Run this inside FLAC's Python, with network access on "
            "first use, then retry."
        ) from exc
    # This add-on already handled install/upgrade above; tell start() to skip
    # its own update check (bridge >= 0.2.0). The env var works across bridge
    # versions, unlike the start(auto_upgrade=...) kwarg older bridges lack.
    os.environ["ITASCA_MCP_BRIDGE_AUTO_UPGRADE"] = "0"
    print("[addon] Starting bridge (ws://localhost:9001) ...")
    bridge.start()


if __name__ == "__main__":
    main()
else:  # pasted into the IPython console as a plain snippet
    main()
