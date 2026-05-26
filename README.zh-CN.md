# flac-mcp

[English](https://github.com/yusong652/flac-mcp/blob/main/README.md) | [简体中文](https://github.com/yusong652/flac-mcp/blob/main/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/flac-mcp)](https://pypi.org/project/flac-mcp/)
[![Downloads](https://static.pepy.tech/badge/flac-mcp)](https://pepy.tech/project/flac-mcp)
[![GitHub stars](https://img.shields.io/github/stars/yusong652/flac-mcp)](https://github.com/yusong652/flac-mcp/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

`flac3d>model new ;now, with LLM.`

**flac-mcp** 通过 [Model Context Protocol](https://modelcontextprotocol.io/) 将 AI 智能体连接到 [ITASCA FLAC](https://www.itascacg.com/software/flac3d) — 浏览文档、运行仿真、执行代码，一切通过自然语言对话完成。

`flac3d>model solve ;LLM solves.`

## 工具（14）

**7 个文档工具** — 浏览和搜索 FLAC 命令、Python API、参考文档，并审计内置命令/Python API 覆盖率。无需 bridge。

**7 个执行工具** — 运行时识别、运行时验证、交互式 REPL、任务提交、进度监控、中断和历史浏览。需要 bridge。

## 运行方式

`flac-mcp` 由两个进程组成：

- MCP 服务端运行在普通 Python 环境中，通过 `uvx flac-mcp` 启动。
- bridge 运行在 FLAC 内嵌 Python 中，通过 [`addon.py`](addon.py) 启动，并监听 `ws://localhost:9002`。

文档工具只要 MCP 服务端注册好就能用。执行工具需要连接 bridge，因为只有 FLAC 内嵌 Python 能 `import itasca` 并操作当前模型。每个会话开始时建议先调用 `flac_get_runtime_info`，确认当前连接的是 FLAC2D/FLAC3D、模型维度和内嵌 Python 信息。

## 首次启动配置

### 前置条件

- 已安装 **ITASCA FLAC 6.0、7.0 或 9.x**
- 已安装 **[uv](https://docs.astral.sh/uv/getting-started/installation/)**（用于 `uvx`）

### 智能体自动配置（推荐）

将以下文本复制给你的 AI 智能体，让它自动完成配置。已知目标产品/版本时一起写明：

```text
Fetch and follow this bootstrap guide end-to-end:
https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap.md

Target runtime: FLAC2D 9.x, or FLAC3D 6.0/7.0/9.x.
```

### 手动配置

**1. 在客户端配置中注册 MCP 服务：**

```json
{
  "mcpServers": {
    "flac-mcp": {
      "command": "uvx",
      "args": ["flac-mcp"]
    }
  }
}
```

**2. 在 FLAC 中启动 bridge：**

下载 [`addon.py`](addon.py)，然后在 FLAC 中任选一种方式执行：

- 把这个文件的内容复制到 FLAC 的 IPython 控制台里运行
- 或者先把这个文件下载到本地，再在 FLAC GUI 里执行它

### 验证

重启你的 AI 智能体（Claude Code、Codex CLI、Gemini CLI 等）。先调用 `flac_get_runtime_info`，确认返回的产品和维度符合当前 FLAC GUI；然后调用 `flac_validate_runtime` 做一次非破坏性的 bridge、命令执行和 `.dat` 文件写读冒烟验证。也可以让它调用 `flac_execute_code` 执行：

```python
import itasca as it
print("FLAC bridge online")
print(it.command("model list information"))
```

如果这一步成功，可以继续用 `flac_execute_task` 验证任务执行，参数传 FLAC 所在机器上真实存在的 Python 脚本绝对路径。

## 日常启动

完成首次配置之后，每次启动 FLAC 只需要把 [`addon.py`](addon.py) 粘进 IPython 控制台运行，bridge 起来后就可以继续用了。MCP 客户端配置会一直保留。

## 功能亮点

- **多版本 FLAC 支持** — 通过 `version` 参数查阅 FLAC 6.0、7.0、9.0-9.7 的命令文档
- **版本化 Python API 快照** — 内置 FLAC3D 6.0、7.0 和 9.x 基线的 Python API 文档
- **按产品区分 Python API 文档** — Python API 浏览/搜索通过 `product` 和 `version` 使用 FLAC2D 或 FLAC3D API 索引
- **FLAC2D/FLAC3D 过滤** — 命令和参考文档工具支持 `product`，减少维度不匹配
- **扩展的 FLAC 9.x Python API** — 内置 attach、array、interface、zone、gridpoint、vec 等 API 文档
- **层级式文档浏览** — 智能体沿着 FLAC 命令树自主发现能力与边界，减少幻觉命令
- **扩展的参考文档** — 在官方文档基础上补充了 plot items、边界条件、初始条件、结构单元属性、FISH intrinsic、interface/joint、geometry/data/table、sketch/building-block、history 与 results 参考文档
- **旧版本命令可用性** — FLAC3D 6.0/7.0 命令覆盖已对照官方旧版命令索引解析；旧版索引不存在的命令会报告为该版本不可用
- **运行时验证** — 一个工具检查 bridge 连通性、运行时身份、安全命令执行，以及临时 `.dat` 文件写读能力
- **交互式 REPL** — 正式编写脚本前快速试错，智能体可以快速迭代验证
- **任务全生命周期管理** — 提交长时仿真、监控进度、中止运行中的任务、浏览历史任务
- **多客户端兼容** — 支持 Claude Code、Codex CLI、Gemini CLI、GitHub Copilot CLI、OpenCode、toyoura-nagisa 等 MCP 客户端

## 故障排查

详见 bootstrap 指南中的[故障排查章节](docs/agentic/flac-mcp-bootstrap.md#troubleshooting)。

## 开发

详见 [开发者指南：从源码安装与运行](docs/development/source-install.zh-CN.md)。

真实 FLAC 软件验证流程见 [FLAC Runtime Validation Checklist](docs/validation/flac-runtime-validation.md)。

项目 wiki 风格文档入口：[docs/wiki/Home.md](docs/wiki/Home.md)。

源码开发建议克隆时带上 submodule：

```bash
git clone --recurse-submodules https://github.com/yusong652/flac-mcp.git
```

如果 clone 或 pull 后 `itasca-mcp-bridge/` 是空目录，执行：

```bash
git submodule update --init --recursive
```

## 贡献

欢迎提交 PR 和 Issue！参见[开发者指南](docs/development/source-install.zh-CN.md)了解如何开始。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
