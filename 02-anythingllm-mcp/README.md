# anythingllm-mcp

将本机安装的 AnythingLLM 暴露给 AI Agent 的 MCP 服务（MVP 版）。

## 技术栈

- Python 3.11+
- MCP Python SDK `mcp==2.0.0`（MCPServer，不使用 FastMCP）
- MCP 协议版本：`2026-07-28`
- 无状态 Streamable HTTP（`stateless_http=True`），不要求 `initialize` / `Mcp-Session-Id`
- HTTP 客户端：`httpx`
- 监听 `127.0.0.1:8765`

## 唯一工具

`ask_first_workspace(message: str) -> str`

向 AnythingLLM 第一个工作区提问，返回 AI 的回答文本。第一个工作区的 slug 在每次调用时动态获取（避免硬编码）。

## 配置项（环境变量）

| 变量 | 默认值 | 必填 | 说明 |
| --- | --- | --- | --- |
| `ANYTHINGLLM_BASE_URL` | `http://localhost:3001` | 否 | AnythingLLM 服务地址 |
| `ANYTHINGLLM_API_KEY` | — | **是** | AnythingLLM Developer API Key |
| `MCP_HOST` | `127.0.0.1` | 否 | MCP 监听地址 |
| `MCP_PORT` | `8765` | 否 | MCP 监听端口 |
| `ANYTHINGLLM_TIMEOUT` | `120` | 否 | 后端 HTTP 超时秒数 |

## 安装

```bash
cd anythingllm-mcp
pip install -e .
```

## 启动 MCP 服务

### 方式 A：直接命令行

PowerShell：

```powershell
$env:ANYTHINGLLM_API_KEY="你的AnythingLLM API Key"
cd anythingllm-mcp
python -m server
```

bash：

```bash
export ANYTHINGLLM_API_KEY="你的AnythingLLM API Key"
cd anythingllm-mcp
python -m server
```

### 方式 B：后台启动（PowerShell）

```powershell
$env:ANYTHINGLLM_API_KEY="你的AnythingLLM API Key"
Start-Process -FilePath python -ArgumentList "-m","server" `
  -WorkingDirectory ".\anythingllm-mcp" `
  -WindowStyle Hidden
```

启动后控制台输出：

```
AnythingLLM MCP 启动中...
  MCP 端点:        http://127.0.0.1:8765/mcp
  健康检查:        http://127.0.0.1:8765/health
  AnythingLLM:     http://localhost:3001
  API Key 已配置:  True
```

## 停止 MCP 服务

### 直接前台运行的进程

在运行 `python -m server` 的终端按 `Ctrl+C`。

### 后台进程

```powershell
# 按端口找进程并结束
$proc = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($proc) { Stop-Process -Id $proc.OwningProcess -Force; "已停止 PID $($proc.OwningProcess)" }
```

### 通过任务名（如果用 Start-Process 启动）

```powershell
Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like '*python*' } | Stop-Process -Force
```

## 验证

### 健康检查

```bash
curl http://127.0.0.1:8765/health
# {"status":"ok","service":"anythingllm-mcp"}
```

### 调用工具

```bash
curl -X POST http://127.0.0.1:8765/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"ask_first_workspace","arguments":{"message":"你好，简单介绍下自己"}}}'
```

## 项目级 MCP 配置

本目录下的 `.mcp.json` 已配置：

```json
{
  "mcpServers": {
    "anythingllm": {
      "url": "http://127.0.0.1:8765/mcp",
      "type": "http"
    }
  }
}
```

IDE/Agent 启动后会自动加载此项目级 MCP 配置。

## 范围声明

MVP 版本仅实现一个工具 `ask_first_workspace`。多工作区切换、流式输出、文档嵌入、线程管理等均未实现。
