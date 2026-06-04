# 开发者指南：从源码安装与运行

这份指南面向需要直接使用本地源码进行开发、在发布到 PyPI 之前验证修改，或将 bridge 从本地源码安装到 FLAC 内嵌 Python 环境中的贡献者。

## 运行时拆分

这个仓库实际上包含两个独立运行时：

- `flac-mcp`
  位于 [`src/flac_mcp`](../../src/flac_mcp) 的 MCP 服务端包，运行在标准 Python `>=3.10`
- `itasca-mcp-bridge`
  位于 [`itasca-mcp-bridge`](../../itasca-mcp-bridge) 的 bridge 包，运行在 FLAC 内嵌 Python 中。这个目录是一个 **git submodule**：它有自己独立的仓库（[`yusong652/itasca-mcp-bridge`](https://github.com/yusong652/itasca-mcp-bridge)）和独立的发版周期。`flac-mcp` 只记录“用 bridge 的哪个 commit”，并不跟踪 bridge 的源文件。

虽然它们出现在同一个工作区里，但安装和验证时应当视为两个独立目标。

## 1. 克隆仓库并安装开发依赖

克隆时带上 bridge submodule（第 3–7 步需要它）：

```bash
git clone --recurse-submodules https://github.com/yusong652/flac-mcp.git
```

已经克隆过、但当时没加 `--recurse-submodules`？此时 `itasca-mcp-bridge/` 是空的，需要初始化：

```bash
git submodule update --init --recursive
```

然后在仓库根目录执行：

```bash
uv sync --group dev
```

运行测试：

```bash
uv run pytest tests
```

### 与 bridge submodule 协作

`itasca-mcp-bridge/` 是一个被钉住的指针（gitlink，模式 `160000`），指向独立仓库 [`yusong652/itasca-mcp-bridge`](https://github.com/yusong652/itasca-mcp-bridge) 的某一个 commit —— `flac-mcp` 在这个路径下只跟踪一个 SHA，而不是 bridge 的源文件。由此带来几点实务：

- **pull `flac-mcp` 之后**，要重新同步指针（submodule 工作区不会自动跟着移动）：

  ```bash
  git submodule update --init --recursive
  ```

- **要升级 bridge 版本**，先在 `itasca-mcp-bridge/` 里 checkout 到目标 commit，然后回到 `flac-mcp` 显式提交这个移动后的指针：

  ```bash
  git add itasca-mcp-bridge && git commit -m "chore: bump itasca-mcp-bridge pin"
  ```

- **推送顺序很重要**：先推 bridge 仓库。被钉住的 commit 必须已经存在于 bridge 公共仓库，否则别人 clone 拉不到。
- `git status` 出现 `modified: itasca-mcp-bridge (untracked content)` 通常只是说 submodule 工作区相对锁定的 commit 有本地/未跟踪文件 —— 并不是 `flac-mcp` 在跟踪 bridge 源码。只有在你确实想升级时才去动这个指针。

## 2. 让 MCP 客户端指向本地源码

如果你希望 MCP 客户端使用本地 checkout 而不是 PyPI 发布版，可以用 `uv run --directory` 指向仓库：

```json
{
  "mcpServers": {
    "flac-mcp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/flac-mcp", "flac-mcp", "--bridge-url", "ws://localhost:9001"]
    }
  }
}
```

`--bridge-url` 参数是可选的（默认 `ws://localhost:9001`）。若 bridge 跑在非默认端口上，
直接用 `--bridge-port` 即可，无需写出整条 URL——例如 bridge 以
`itasca_mcp_bridge.start(port=9002)` 启动时，配置写
`"args": [..., "flac-mcp", "--bridge-port", "9002"]`。

这是验证 MCP 侧改动最简单的方式，不需要先构建或发布包。

## 3. 直接从源码启动 Bridge

如果你只是想让 bridge 侧代码修改在 FLAC 中生效，其实不需要先安装 bridge 包。在 FLAC 的 IPython 控制台里执行：

```python
%run C:/path/to/flac-mcp/itasca-mcp-bridge/start_bridge.py
```

注意：

- 路径请使用正斜杠
- `%run` 后面的路径不要加引号
- 修改 bridge 源码后需要重启 bridge

这是 bridge 开发时最快的工作流。

## 4. 将 Bridge 从本地源码安装到内嵌 Python

如果你要验证“包安装路径”本身，而不只是直接 `%run`，建议从终端调用 FLAC 的内嵌 Python 解释器，把 `itasca-mcp-bridge` 从本地源码安装进去。

先根据 FLAC 版本选择正确解释器：

- FLAC `6.0` / `7.0`：`C:/Program Files/Itasca/.../exe64/python36/python.exe`
- FLAC `9.0`：`C:/Program Files/Itasca/.../exe64/python310/python.exe`

示例命令：

```powershell
& "C:\Program Files\Itasca\FLAC700\exe64\python36\python.exe" -m pip install --user -e C:\path\to\flac-mcp\itasca-mcp-bridge
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -m pip install --user -e C:\path\to\flac-mcp\itasca-mcp-bridge
```

为什么推荐在终端里直接调用内嵌解释器：

- 安装目标就是 FLAC 实际使用的那个 Python 环境
- 不依赖在 FLAC 控制台里通过 `subprocess` 再起一个解释器
- 对 editable install 来说最稳定

bridge 包会自动拉取匹配的 `websockets` 版本：

- Python `3.6` -> `websockets==9.1`
- Python `3.10` -> `websockets==16.0`

## 5. 在 FLAC IPython 中安装

如果你是在 FLAC 控制台里直接安装 PyPI 版本，请使用主 README 中那段按版本分支的安装代码：

- FLAC `6.0` / `7.0`：`pip.main(...)`
- FLAC `9.0`：`pip._internal.cli.main.main(...)`

如果是“从源码安装”，更推荐使用上面第 4 步那种“终端 + 内嵌解释器”的方式，而不是在 FLAC GUI 控制台里尝试驱动 editable install。

## 6. 验证环境

可以先在内嵌 Python 里检查 bridge 包和 `websockets`：

```powershell
& "C:\Program Files\Itasca\ItascaSoftware900\exe64\python310\python.exe" -c "import itasca_mcp_bridge, websockets; print(itasca_mcp_bridge.__version__); print(websockets.__version__)"
```

然后在 FLAC 中启动 bridge，并从 MCP 客户端验证：

1. 在 FLAC 中执行 `itasca_mcp_bridge.start()` 或 `%run .../start_bridge.py`
2. 重启 MCP 客户端会话
3. 调用 `flac_list_tasks`

## 7. 推荐开发循环

对于大多数日常开发，推荐这样做：

1. 执行 `uv sync --group dev`
2. 用 `uv run --directory` 让 MCP 客户端指向本地源码
3. 在 FLAC 中用 `%run .../itasca-mcp-bridge/start_bridge.py` 启动 bridge
4. 执行 `uv run pytest tests`
5. 修改后按需重启 MCP 客户端和 bridge
