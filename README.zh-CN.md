# flac-mcp

<p align="center">
  <img src="https://raw.githubusercontent.com/yusong652/flac-mcp/assets/header.png" width="70%" alt="flac-mcp — MCP Server for ITASCA FLAC">
</p>

[English](https://github.com/yusong652/flac-mcp/blob/main/README.md) | [简体中文](https://github.com/yusong652/flac-mcp/blob/main/README.zh-CN.md)

[![PyPI](https://img.shields.io/pypi/v/flac-mcp)](https://pypi.org/project/flac-mcp/)
[![Downloads](https://static.pepy.tech/badge/flac-mcp)](https://pepy.tech/project/flac-mcp)
[![GitHub stars](https://img.shields.io/github/stars/yusong652/flac-mcp)](https://github.com/yusong652/flac-mcp/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

`flac3d>model new ;now, with LLM.`

**flac-mcp** 通过 [Model Context Protocol](https://modelcontextprotocol.io/) 将 AI 智能体连接到 [ITASCA FLAC](https://www.itascacg.com/software/flac3d) — 浏览文档、运行仿真、执行代码，一切通过自然语言对话完成。

`flac3d>model solve ;LLM solves.`

## 工具（10）

**5 个文档工具** — 浏览和搜索 FLAC 命令、Python API 及参考文档。无需 bridge。

**5 个执行工具** — 交互式 REPL、任务提交、进度监控、中断和历史浏览。需要 bridge。

## 首次启动配置

### 前置条件

- 已安装 **ITASCA FLAC 6.0、7.0 或 9.0**
- 已安装 **[uv](https://docs.astral.sh/uv/getting-started/installation/)**（用于 `uvx`）

### 智能体自动配置（推荐）

将以下文本复制给你的 AI 智能体，让它自动完成配置：

```text
请全程用中文与我交流。然后获取并完整按照这份引导指南执行（指南为英文，照其步骤操作即可）：
https://raw.githubusercontent.com/yusong652/flac-mcp/main/docs/agentic/flac-mcp-bootstrap.md
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

重启你的 AI 智能体（Claude Code、Codex CLI、Gemini CLI 等），让它调用 `flac_execute_code` 来验证连接是否正常。

## 日常启动

完成首次配置之后，每次启动 FLAC 只需要在 IPython 控制台里运行下面两行，bridge 起来后就可以继续用了：

```python
import itasca_mcp_bridge
itasca_mcp_bridge.start()
```

`start()` 会先检查 PyPI 上是否有新版 bridge，有则自动升级再启动（尽力而为：离线时直接启动已安装版本；传 `auto_upgrade=False` 可锁定版本）。MCP 客户端配置会一直保留。

## 功能亮点

- **多版本 FLAC 支持** — 通过 `version` 参数查阅 FLAC 6.0、7.0、9.0 的命令文档
- **层级式文档浏览** — 智能体沿着 FLAC 命令树自主发现能力与边界，减少幻觉命令
- **增强的 plot 文档** — 在官方文档基础上补充了 plot items 参考文档
- **交互式 REPL** — 正式编写脚本前快速试错，智能体可以快速迭代验证
- **任务全生命周期管理** — 提交长时仿真、监控进度、中止运行中的任务、浏览历史任务
- **多客户端兼容** — 支持 Claude Code、Codex CLI、Gemini CLI、GitHub Copilot CLI、OpenCode、toyoura-nagisa 等 MCP 客户端

## 故障排查

详见 bootstrap 指南中的[故障排查章节](docs/agentic/flac-mcp-bootstrap.md#troubleshooting)。

## 开发

详见 [开发者指南：从源码安装与运行](docs/development/source-install.zh-CN.md)。

## 贡献

欢迎提交 PR 和 Issue！参见[开发者指南](docs/development/source-install.zh-CN.md)了解如何开始。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
