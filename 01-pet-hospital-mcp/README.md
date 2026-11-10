# pet-hospital-mcp

独立的 Python MCP 服务，将 Go 宠物医院 REST API 的能力暴露给 AI Agent。

## 技术栈

- Python 3.11+
- MCP Python SDK：`mcp==2.0.0`
- MCP 协议版本：`2026-07-28`
- 使用 SDK 2.x 的 `MCPServer`（**不**使用 `mcp.server.fastmcp.FastMCP`）
- 无状态 Streamable HTTP 模型：不实现旧协议的 `initialize`、`Mcp-Session-Id`、会话存储、会话过期或 `max_sessions`
- HTTP 客户端：`httpx`
- 数据校验：`pydantic` v2
- 结构化日志：`structlog`（JSON 输出，对 `ownerPhone`、`ownerAddr`、`chipNo` 递归脱敏）

## 目录结构

```text
pet-hospital-mcp/
├── pyproject.toml
├── README.md
├── UPGRADE_PROMPT.md
├── src/
│   └── pet_hospital_mcp/
│       ├── __init__.py
│       ├── __main__.py          # 入口
│       ├── config.py            # 环境变量配置
│       ├── server.py            # MCPServer 装配与工具注册
│       ├── rest_client.py        # Go REST API 客户端
│       ├── errors.py            # 统一错误结构
│       ├── logging_config.py    # structlog + 脱敏
│       └── tools/
│           ├── __init__.py
│           └── list_pets.py     # 唯一 MCP 工具
└── tests/
    ├── conftest.py
    ├── test_rest_client.py
    ├── test_server.py
    └── test_validation.py
```

## 前置条件

### 1. 启动 Go REST API（必须先启动）

MCP 服务通过 HTTP 调用 Go 宠物医院服务，必须先启动上游：

```bash
cd D:/大模型课程教学/pet-hospital-mcp-teaching
go run main.go
# 或使用预编译二进制
./pet-hospital-mcp-teaching.exe
```

默认监听 `http://127.0.0.1:8080`。

### 2. 安装 MCP 服务依赖

```bash
cd pet-hospital-mcp
pip install -e .
# 开发/测试依赖
pip install -e ".[dev]"
```

## 配置项（环境变量）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `MCP_HOST` | `127.0.0.1` | MCP 服务监听地址 |
| `MCP_PORT` | `8000` | MCP 服务监听端口 |
| `PET_HOSPITAL_BASE_URL` | `http://127.0.0.1:8080` | Go REST API 地址 |
| `BACKEND_TIMEOUT_SECONDS` | `10.0` | 后端 HTTP 调用超时秒数 |
| `BACKEND_MAX_RETRIES` | `2` | 后端调用最大重试次数（超时/连接异常时） |

## MCP 端点

- MCP Streamable HTTP 端点：`http://<MCP_HOST>:<MCP_PORT>/mcp`
- 健康检查：`http://<MCP_HOST>:<MCP_PORT>/health`

无状态：不要求客户端先发送 `initialize`，不返回 `Mcp-Session-Id`，不保存会话状态。

## 启动 MCP 服务

```bash
cd pet-hospital-mcp
python -m pet_hospital_mcp
```

自定义配置：

```bash
# PowerShell
$env:MCP_HOST="127.0.0.1"
$env:MCP_PORT="8000"
$env:PET_HOSPITAL_BASE_URL="http://127.0.0.1:8080"
python -m pet_hospital_mcp
```

```bash
# bash
MCP_HOST=127.0.0.1 MCP_PORT=8000 \
PET_HOSPITAL_BASE_URL=http://127.0.0.1:8080 \
python -m pet_hospital_mcp
```

## 验证

### 方式 A：MCP Inspector

```bash
npx @modelcontextprotocol/inspector python -m pet_hospital_mcp
```

Inspector 中：
- Transport：`Streamable HTTP`
- URL：`http://127.0.0.1:8000/mcp`
- 直接调用 `tools/list` 发现 `list_pets`
- 调用 `tools/call` 传入参数测试

### 方式 B：curl

健康检查：

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","service":"pet-hospital-mcp"}
```

向 MCP 端点发送 `tools/list`（无需 `initialize`）：

```bash
curl -s -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

调用 `list_pets`：

```bash
curl -s -X POST http://127.0.0.1:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"list_pets","arguments":{"species":"犬","page":1,"pageSize":10}}}'
```

### 方式 C：SDK 2.x 客户端

```python
import asyncio
from mcp.client import Client

async def main():
    async with Client("http://127.0.0.1:8000/mcp") as client:
        tools = (await client.list_tools()).tools
        print([t.name for t in tools])  # ['list_pets']
        result = await client.call_tool("list_pets", {"species": "犬", "page": 1, "pageSize": 10})
        print(result.is_error, result.structured_content)

asyncio.run(main())
```

## list_pets 工具说明

适配 Go REST API `GET /api/v1/pets`，仅支持以下 14 个查询参数：

| 参数 | 类型 | 校验 |
| --- | --- | --- |
| `q` | str | 全文检索关键词 |
| `name` | str | 宠物姓名（模糊） |
| `ownerName` | str | 主人姓名（模糊） |
| `ownerPhone` | str | 主人电话（模糊） |
| `species` | Literal | 犬/猫/兔/鸟/仓鼠/爬宠/其他 |
| `doctor` | str | 主治医生（模糊） |
| `disease` | str | 疾病（模糊） |
| `status` | Literal | 待就诊/就诊中/住院中/已康复/慢性病随访 |
| `min` | float | 最低总花费，非负 |
| `max` | float | 最高总花费，非负，且 `min <= max` |
| `sortBy` | Literal | id/name/ownerName/species/doctor/disease/status/totalCost/visitCount/createdAt/updatedAt |
| `order` | Literal | asc/desc |
| `page` | int | `>= 1` |
| `pageSize` | int | `1 <= pageSize <= 500` |

输入额外约束：
- 拒绝未知字段（`extra="forbid"`）
- 拒绝 `NaN` / `Infinity`
- 拒绝类型不正确

成功返回（对应 Go 响应 `data`）：`items`、`total`、`page`、`pageSize`、`totalPages`、`totalCost`。`items` 中的 `records`、`charges` 兼容 Go 的 `null` 或数组两种 JSON 表现。

失败返回统一错误结构：

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "可读错误信息",
    "details": {}
  }
}
```

错误码：`VALIDATION_ERROR`、`BACKEND_TIMEOUT`、`BACKEND_UNAVAILABLE`、`BACKEND_API_ERROR`、`BACKEND_INVALID_RESPONSE`、`INTERNAL_ERROR`。

## 单元测试

测试使用 `httpx.MockTransport`，**不访问真实 Go 服务**。

```bash
cd pet-hospital-mcp
pytest -q
```

预期结果：

```text
...............................................................    [100%]
63 passed in 1.17s
```

覆盖范围：
1. 正常调用：确认请求路径与全部过滤/排序/分页参数正确转发
2. 输入参数校验失败（species/status/sortBy/order/page/pageSize/min/max/未知字段/NaN/Infinity/类型错误）
3. Go REST API 返回 4xx / 5xx
4. 超时与连接异常
5. 后端返回非法 JSON 或不符合数据模型
6. MCP 工具注册、工具名与 JSON Schema
7. SDK 2.x 无状态连接流程：不发送 `initialize`、不要求 `Mcp-Session-Id`、`/health` 端点、`/mcp` 可发现并调用工具

## 范围声明

本次实现仅包含一个 MCP 工具 `list_pets`。**未实现阶段二工具**（新增/更新/删除宠物、病历、收费明细等写操作工具）。
