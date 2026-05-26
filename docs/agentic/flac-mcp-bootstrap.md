# flac-mcp Agent Bootstrap Guide

Use this guide when an agent needs to set up `flac-mcp` execution end-to-end on a Windows machine.

## Target Outcome

1. MCP client is configured to run `flac-mcp`.
2. The target FLAC product and version are known: FLAC2D or FLAC3D, 6.0, 7.0, or 9.0.
3. `itasca-mcp-bridge` is installed in that FLAC installation's embedded Python environment.
4. The bridge is started inside the matching FLAC GUI through `addon.py` or `itasca_mcp_bridge.start()`.
5. MCP execution tools are verified with `flac_get_runtime_info` and `flac_execute_code`.

## Supported Runtime Matrix

| Product | Version | Embedded Python | Execution support | Documentation support |
| --- | --- | --- | --- | --- |
| FLAC2D | 6.0 | N/A | Not applicable in this documentation matrix | Not applicable |
| FLAC2D | 7.0 | N/A | Not applicable in this documentation matrix | Not applicable |
| FLAC2D | 9.0 | Python 3.10 | Supported | Product-scoped command/reference/Python API docs available |
| FLAC3D | 6.0 | Python 3.6 | Supported | Product-scoped command/reference/Python API docs available |
| FLAC3D | 7.0 | Python 3.6 | Supported | Product-scoped command/reference/Python API docs available |
| FLAC3D | 9.0 | Python 3.10 | Supported | Product-scoped command/reference/Python API docs available |

Execution support depends on the installed GUI process and its embedded Python. Documentation tools do not need a running bridge.

## Agent Execution Rules

- Resolve the user's intended product before launching or attaching to FLAC. Do not assume FLAC3D if both FLAC2D and FLAC3D are installed.
- Use bounded, fast path detection for `flac_path`; avoid full-drive recursive scans by default.
- Prefer FLAC embedded interpreter for package installs:
  - FLAC 6.0/7.0: `"{flac_path}/exe64/python36/python.exe" -m pip ...`
  - FLAC 9.0: `"{flac_path}/exe64/python310/python.exe" -m pip ...`
- If a command or API lookup is product-sensitive, pass `product="flac2d"` or `product="flac3d"` explicitly.
- If a setup step fails, report the exact command and output, then apply the next fallback.
- Respect step ownership labels:
  - `[AGENT]` means the agent should execute the action.
  - `[USER ACTION REQUIRED]` means the user must execute it manually.

## Step 0 - Choose Product and Version

[AGENT]

Ask only when the intent is ambiguous. If the user has already specified a product/version, use it.

Record these values before continuing:

```text
target_product = flac2d | flac3d
target_version = 6.0 | 7.0 | 9.0
```

Valid product/version combinations in the bundled documentation matrix:

- `flac2d` + `9.0`
- `flac3d` + `6.0`, `7.0`, or `9.0`

Use those values consistently when browsing docs:

- Commands: `flac_browse_commands(product=target_product, version=target_version)`
- Command search: `flac_query_command(product=target_product, version=target_version)`
- Reference docs: `flac_browse_reference(product=target_product, version=target_version)`
- Python API docs: `flac_browse_python_api(product=target_product, version=target_version)`
- Python API search: `flac_query_python_api(product=target_product, version=target_version)`

Do not use FLAC3D-only examples with FLAC2D until runtime verification proves they are valid.

## Step 1 - Configure MCP Client

[AGENT]

Use the client-specific Step 1 profile:

- OpenCode: https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap-opencode.md
- Claude Code: https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap-claude.md
- Codex: https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap-codex.md
- Gemini CLI: https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap-gemini.md
- GitHub Copilot CLI: https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap-copilot.md
- toyoura-nagisa: https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap-toyoura-nagisa.md

If raw URL fetch is unavailable, use repository-relative paths:

- `docs/agentic/flac-mcp-bootstrap-opencode.md`
- `docs/agentic/flac-mcp-bootstrap-claude.md`
- `docs/agentic/flac-mcp-bootstrap-codex.md`
- `docs/agentic/flac-mcp-bootstrap-gemini.md`
- `docs/agentic/flac-mcp-bootstrap-copilot.md`
- `docs/agentic/flac-mcp-bootstrap-toyoura-nagisa.md`

Apply this MCP launch contract in your client's native config format:

- server id/name: `flac-mcp`
- primary launch command: `uvx flac-mcp`
- fallback launch command: `uv tool run flac-mcp`
- bridge URL default: `ws://localhost:9002`
- enable server in client config
- prefer workspace-level config by default; use global config only if user explicitly requests it

When editing MCP config, use this order:

1. If config file does not exist, create it.
2. If config exists but has no `flac-mcp` entry, merge/add only that entry.
3. If `flac-mcp` already exists, validate/update only MCP launch fields (`command`, `args`, `env`, and client-specific extras).
4. Do not overwrite unrelated MCP servers.

For a non-default bridge URL, pass `--bridge-url` to `flac-mcp` or set `FLAC_MCP_BRIDGE_URL` in the MCP server environment. The FLAC bridge itself must be started on the same URL/port.
When using `addon.py`, set `FLAC_MCP_BRIDGE_PORT` in the FLAC process environment before launch if the bridge must listen on a port other than `9002`.

## Step 2 - Resolve `flac_path`

[AGENT]

`flac_path` is the FLAC install directory containing `exe64/flac2d*_gui.exe` or `exe64/flac3d*_gui.exe`.

### 2.0 Quick Probe

Try lightweight checks first:

```powershell
Get-ChildItem "C:\Program Files\Itasca" -Directory -ErrorAction SilentlyContinue
Get-ChildItem "D:\Program Files\Itasca" -Directory -ErrorAction SilentlyContinue
```

If obvious install folders are found, immediately drill into those folders and check `exe64/flac*_gui.exe` before running broader lookup.

### 2.1 Bounded Common-Path Lookup

Run in PowerShell:

```powershell
$roots=@('C:\Program Files\Itasca','D:\Program Files\Itasca','C:\Itasca','D:\Itasca');
$hits=@();
foreach($r in $roots){
  if(Test-Path $r){
    Get-ChildItem -Path $r -Directory -ErrorAction SilentlyContinue | ForEach-Object {
      $exeDir=Join-Path $_.FullName 'exe64';
      if(Test-Path $exeDir){
        Get-ChildItem -Path $exeDir -Filter 'flac*_gui.exe' -File -ErrorAction SilentlyContinue | ForEach-Object {
          $name=$_.BaseName.ToLowerInvariant();
          $product=if($name -match 'flac2d'){'flac2d'}elseif($name -match 'flac3d'){'flac3d'}else{'unknown'};
          $version=if($name -match '(?<major>[679])00'){"$($Matches.major).0"}else{'unknown'};
          $py310=Join-Path $exeDir 'python310\python.exe';
          $py36=Join-Path $exeDir 'python36\python.exe';
          $python=if(Test-Path $py310){$py310}elseif(Test-Path $py36){$py36}else{''};
          $hits += [PSCustomObject]@{
            product=$product;
            version=$version;
            flac_path=$_.Directory.Parent.FullName;
            gui_exe=$_.FullName;
            python=$python
          }
        }
      }
    }
  }
}
$hits | Sort-Object product,version,gui_exe -Unique | Format-Table -AutoSize
```

Select the row matching `target_product` and `target_version`. If multiple rows match, ask the user which installation to use.

### 2.2 Optional Registry Lookup

Some installations are not registered in Windows uninstall keys; treat this as a fallback.

```powershell
$keys=@('HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*','HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*');
$hits=@();
foreach($k in $keys){
  Get-ItemProperty $k -ErrorAction SilentlyContinue |
    Where-Object { $_.DisplayName -match 'FLAC|Itasca' } |
    ForEach-Object {
      if($_.InstallLocation){
        $exeDir=Join-Path $_.InstallLocation 'exe64';
        Get-ChildItem -Path $exeDir -Filter 'flac*_gui.exe' -File -ErrorAction SilentlyContinue | ForEach-Object {
          $name=$_.BaseName.ToLowerInvariant();
          $product=if($name -match 'flac2d'){'flac2d'}elseif($name -match 'flac3d'){'flac3d'}else{'unknown'};
          $version=if($name -match '(?<major>[679])00'){"$($Matches.major).0"}else{'unknown'};
          $hits += [PSCustomObject]@{
            product=$product;
            version=$version;
            flac_path=$_.Directory.Parent.FullName;
            gui_exe=$_.FullName
          }
        }
      }
    }
}
$hits | Sort-Object product,version,gui_exe -Unique | Format-Table -AutoSize
```

If still unresolved, ask the user to provide the exact `flac_path`.

## Step 3 - Install/Upgrade Bridge in FLAC Python

[AGENT]

Resolve `flac_python` from the selected FLAC installation:

- FLAC 6.0/7.0: `{flac_path}/exe64/python36/python.exe`
- FLAC 9.0: `{flac_path}/exe64/python310/python.exe`

Check current package:

```powershell
& "{flac_python}" -m pip show itasca-mcp-bridge
```

Install or upgrade:

```powershell
& "{flac_python}" -m pip install --user --upgrade itasca-mcp-bridge
```

If PyPI access is slow or blocked, retry with a mirror:

```powershell
& "{flac_python}" -m pip install --user --upgrade itasca-mcp-bridge -i https://pypi.tuna.tsinghua.edu.cn/simple
```

Verify import and dependency versions:

```powershell
& "{flac_python}" -c "import itasca_mcp_bridge, websockets; print(itasca_mcp_bridge.__version__); print(websockets.__version__)"
```

The bridge package should install the matching `websockets` dependency automatically:

- Python 3.6: `websockets==9.1`
- Python 3.10: `websockets==16.0`

If dependency errors still appear, install the matching version explicitly:

```powershell
# FLAC 6.0/7.0
& "{flac_python}" -m pip install --user websockets==9.1

# FLAC 9.0
& "{flac_python}" -m pip install --user websockets==16.0
```

Ignore pip upgrade warnings in this environment if package install completed successfully. Older embedded interpreters commonly ship older pip builds.

## Step 4 - Start Bridge in the Selected FLAC GUI

[AGENT]

If the selected FLAC GUI is not open yet, start the selected `gui_exe` from Step 2:

```powershell
Start-Process "{gui_exe}"
```

Confirm the selected product process is running:

```powershell
$procs=Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^flac(2d|3d)\d+_gui\.exe$' };
if($procs){$procs | Select-Object Name,ProcessId,ExecutablePath | Format-Table -AutoSize} else {Write-Output 'No FLAC GUI process found'}
```

If multiple FLAC GUI processes are running and the user did not specify one, ask which one should own the bridge.

Download `addon.py` to a local path the user can easily find:

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/yusong652/flac-mcp/main/addon.py" -OutFile "addon.py"
```

Tell the user where the file was saved.

[USER ACTION REQUIRED]

Use one of these two options to start the bridge in the selected FLAC GUI, then restart the MCP client session before Step 5.

**Option A (recommended):** Open the downloaded `addon.py` in FLAC GUI and execute it, or copy its contents into the FLAC IPython console and run them. The script handles bridge install, upgrade, dependency resolution, and startup.

**Option B (manual):** In the FLAC GUI Python console:

```python
import itasca_mcp_bridge
itasca_mcp_bridge.start()
```

Expected output includes:

- `FLAC Bridge Server`
- `ws://localhost:9002`
- `Bridge started in non-blocking mode`

## Step 5 - Verify from MCP Client

[AGENT]

After the user restarts the MCP client session, first confirm the execution tools are visible. Then call `flac_get_runtime_info`.

Expected successful fields include:

- `product`: should match `target_product`
- `version`: should match `target_version` when the runtime can report it
- `dimension`: `2` for FLAC2D, `3` for FLAC3D
- `python`: embedded Python details from the selected FLAC runtime
- `executable`: should point at the selected FLAC GUI process

If product or dimension does not match, stop and resolve the wrong FLAC process before running user model code.

Then call `flac_execute_code` with:

```python
import itasca as it
print("FLAC bridge online")
print(it.command("model list information"))
```

Success example shape may vary by client:

```json
{
  "ok": true,
  "data": {
    "stdout": "FLAC bridge online\n...",
    "result": null
  }
}
```

`ok: true` means the full MCP -> bridge -> FLAC pipeline is working.

Optional final checks:

- Call `flac_list_tasks` to verify task API connectivity.
- Call `flac_command_coverage` to see which bundled commands are available for the target product/version.
- Call `flac_python_api_coverage` to see which bundled docs are complete for the target product/version.
- Browse one product-scoped command/API before generating model code, especially when targeting FLAC2D.

## Daily Startup

After first-time setup, each new FLAC session only needs:

1. Open the intended FLAC2D or FLAC3D GUI.
2. Run `addon.py` inside that GUI.
3. Restart or reconnect the MCP client if tools were loaded before the bridge was started.
4. Call `flac_get_runtime_info` and confirm product/dimension before executing model code.

The MCP client config persists.

## Troubleshooting

- `Connection refused`:
  - Bridge is not running in the selected FLAC GUI, the wrong port is configured, or port `9002` is unavailable.
- `Port 9002 is already in use`:
  - Close the other Itasca bridge process, or start FLAC with `FLAC_MCP_BRIDGE_PORT` set to another port and point `flac-mcp --bridge-url` at the same port.
- `flac_get_runtime_info` reports the wrong product or dimension:
  - The bridge is attached to a different FLAC GUI process. Close the wrong process or restart the bridge in the selected GUI.
- `No module named itasca_mcp_bridge`:
  - Bridge package is not installed in that FLAC installation's embedded Python.
- `No module named websockets`:
  - Install `websockets==9.1` for FLAC 6/7 or `websockets==16.0` for FLAC 9 in the embedded Python environment.
- `status remains pending` or long task output never updates:
  - Upgrade to the latest `itasca-mcp-bridge` release in the selected FLAC embedded Python.
- `pip` upgrade warning after install:
  - Usually safe to ignore if package install completed successfully.
- Need to confirm GUI process from terminal:
  - Run the process filter command from Step 4 and verify `ExecutablePath`.
- `flac_*` tools missing in client after setup:
  - Client session was not fully restarted after Step 1. Close/reopen client session and retry Step 5.
- PowerShell error `Unexpected token '-m'`:
  - Quoted executable path was not invoked with `&`. Use `& "{flac_python}" -m ...`.
- FLAC2D code fails on `z` coordinates or 3D-only APIs:
  - Re-run documentation lookup with `product="flac2d"` and use runtime `dimension == 2` as the hard boundary.
