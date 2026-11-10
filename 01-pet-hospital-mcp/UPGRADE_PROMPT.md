# UPGRADE_PROMPT — 阶段二扩展提示词

> 本文件用于后续在阶段二为 `pet-hospital-mcp` 增补 MCP 工具。请将本文件全文作为新会话的输入提示词。

你是一位精通 Model Context Protocol（MCP）和 Python 的专家开发者。当前仓库 `pet-hospital-mcp/` 已实现阶段一：

- Python 3.11+，官方 SDK `mcp==2.0.0`，协议版本 `2026-07-28`
- 使用 SDK 2.x 的 `MCPServer`，无状态 Streamable HTTP 模型
- 已实现唯一工具 `list_pets`，适配 Go REST API `GET /api/v1/pets`，14 个查询参数
- 统一错误结构、Pydantic 输入/输出模型、structlog 脱敏日志、httpx 客户端带超时重试
- 测试位于 `tests/`，使用 `httpx.MockTransport`，共 63 个用例全部通过
- **未实现阶段二工具**（写操作类工具）

## 阶段二目标

在不破坏阶段一契约的前提下，新增以下 MCP 工具，严格适配 Go REST API 现有接口：

### 必须新增的工具

1. `get_pet_by_id` — 对应 `GET /api/v1/pets/{id}`
2. `create_pet` — 对应 `POST /api/v1/pets`
3. `update_pet` — 对应 `PUT /api/v1/pets/{id}`（全量更新）
4. `patch_pet` — 对应 `PATCH /api/v1/pets/{id}`（局部更新）
5. `delete_pet` — 对应 `DELETE /api/v1/pets/{id}`
6. `search_pets` — 对应 `GET /api/v1/pets/search`
7. `list_pet_records` — 对应 `GET /api/v1/pets/{id}/records`
8. `add_pet_record` — 对应 `POST /api/v1/pets/{id}/records`
9. `list_pet_charges` — 对应 `GET /api/v1/pets/{id}/charges`
10. `add_pet_charge` — 对应 `POST /api/v1/pets/{id}/charges`

可选工具（视后端可用性而定）：
- `get_pet_stats` — `GET /api/v1/stats`
- `list_endpoints` — `GET /api/v1/endpoints`
- `list_meta` — `GET /api/v1/meta`

## 强制约束

1. **不得修改阶段一已发布工具 `list_pets` 的输入输出契约。**
2. **不得引入 SDK 1.x 的 `FastMCP` 或旧协议机制**（`initialize`、`Mcp-Session-Id`、会话存储）。
3. 每个新工具：
   - 使用 `snake_case` 命名
   - 使用 Pydantic 定义输入/成功/错误模型
   - 复用 `rest_client.py`、`errors.py`、`logging_config.py` 的既有约定
   - 工具描述必须包含用途、参数、适用场景、返回值
   - 不新增适配器私有业务参数
4. 写操作工具必须明确说明对 Go REST API 的副作用。
5. 所有新工具的输入必须：
   - 拒绝未知字段
   - 拒绝 `NaN` / `Infinity`
   - 校验 `species`/`status` 等枚举使用真实后端允许值
   - 对路径参数（如 `id`）做格式校验（如 `PET-dddddd`）
6. 错误处理沿用统一结构，至少区分：`VALIDATION_ERROR`、`BACKEND_TIMEOUT`、`BACKEND_UNAVAILABLE`、`BACKEND_API_ERROR`、`BACKEND_INVALID_RESPONSE`、`INTERNAL_ERROR`。可按需新增如 `BACKEND_CONFLICT`（409）、`BACKEND_NOT_FOUND`（404）等细化错误码，但需在 `errors.py` 中登记并补测试。
7. 日志继续脱敏 `ownerPhone`、`ownerAddr`、`chipNo` 及其 snake_case 写法。
8. 测试使用 `pytest` + `pytest-asyncio` + `httpx.MockTransport`，**禁止访问真实 Go 服务**。每个新工具至少覆盖：
   - 正常调用（参数转发、路径拼接正确）
   - 输入校验失败
   - 4xx / 5xx / 超时 / 连接异常 / 非法 JSON
9. 测试运行命令保持：`cd pet-hospital_mcp; pytest -q`，且原有 63 个用例继续通过。

## 推荐实施流程

1. 阅读 `internal/api/api.go` 中对应路由的真实参数与请求体定义
2. 在 `tools/` 下新增模块（每个工具一个文件或按资源聚合）
3. 在 `rest_client.py` 中新增对应方法，复用 `_get_with_retry` / `_parse_response`，并补 POST/PUT/PATCH/DELETE 的统一处理
4. 在 `server.py` 用 `@mcp.tool()` 注册新工具
5. 为每个工具编写测试，扩展 `tests/`
6. 更新 README.md，补充新工具说明、调用示例与测试结果

## 不得做的事

- 不得修改阶段一 `list_pets` 工具的对外行为
- 不得自行新增阶段三工具（聚合查询、统计报表等），除非本文件明确列出
- 不得引入鉴权、CORS、Origin 校验（教学场景保持无鉴权）
- 不得让 MCP 服务直连数据库或绕过 Go REST API
