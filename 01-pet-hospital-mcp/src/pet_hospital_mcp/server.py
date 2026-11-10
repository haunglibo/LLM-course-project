"""MCP 服务装配。

使用 SDK 2.x 的 MCPServer，无状态 Streamable HTTP 模型。
不使用 mcp.server.fastmcp.FastMCP。
"""

from __future__ import annotations

import time
import traceback

from mcp.server import MCPServer
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from .config import Settings, load_settings
from .errors import ErrorCode, ToolError
from .logging_config import get_logger, redact_params
from .rest_client import PetHospitalClient
from .tools.list_pets import ListPetsInput, ListPetsSuccess

# 全局 MCPServer 实例
mcp = MCPServer("pet-hospital-mcp")

# 全局配置与客户端（在 create_app 中初始化）
_settings: Settings | None = None
_client: PetHospitalClient | None = None


def _get_client() -> PetHospitalClient:
    """获取或懒初始化 REST 客户端。"""
    global _settings, _client
    if _client is None:
        _settings = load_settings()
        _client = PetHospitalClient(_settings)
    return _client


@mcp.tool()
async def list_pets(
    q: str | None = None,
    name: str | None = None,
    ownerName: str | None = None,
    ownerPhone: str | None = None,
    species: str | None = None,
    doctor: str | None = None,
    disease: str | None = None,
    status: str | None = None,
    min: float | None = None,
    max: float | None = None,
    sortBy: str | None = None,
    order: str | None = None,
    page: int | None = None,
    pageSize: int | None = None,
) -> ListPetsSuccess:
    """查询宠物档案列表（对应 Go REST API: GET /api/v1/pets）。

    用途：
        获取宠物医院系统中宠物档案的列表，支持全文检索、
        多字段模糊匹配、种类/状态精确筛选、费用区间过滤、
        排序和分页。

    参数：
        q          全文检索关键词（跨字段，空格分词 AND）
        name       宠物姓名（模糊匹配）
        ownerName  主人姓名（模糊匹配）
        ownerPhone 主人电话（模糊匹配）
        species     宠物种类，可选：犬/猫/兔/鸟/仓鼠/爬宠/其他
        doctor     主治医生（模糊匹配）
        disease    疾病（模糊匹配）
        status     就诊状态，可选：待就诊/就诊中/住院中/已康复/慢性病随访
        min         最低总花费（非负）
        max         最高总花费（非负，须 >= min）
        sortBy      排序字段，可选：id/name/ownerName/species/doctor/
                    disease/status/totalCost/visitCount/createdAt/updatedAt
        order       排序方向：asc/desc
        page        页码，从 1 开始
        pageSize    每页条数，1-500

    适用场景：
        AI Agent 需要查询宠物档案、搜索病历、按条件筛选宠物、
        获取消费排行榜或导出数据时的第一步。

    返回值：
        成功时返回 ListPetsSuccess，包含 items（宠物列表）、
        total（总条数）、page、pageSize、totalPages、totalCost。
        失败时返回统一错误信封 {"error": {...}}。
    """
    logger = get_logger("list_pets")
    start = time.monotonic()
    raw_params = {
        "q": q, "name": name, "ownerName": ownerName,
        "ownerPhone": ownerPhone, "species": species, "doctor": doctor,
        "disease": disease, "status": status, "min": min, "max": max,
        "sortBy": sortBy, "order": order, "page": page, "pageSize": pageSize,
    }
    safe_params = redact_params(raw_params)

    try:
        # 1. Pydantic 输入校验
        try:
            inp = ListPetsInput(**{
                k: v for k, v in raw_params.items() if v is not None
            })
        except Exception as exc:
            raise ToolError(
                ErrorCode.VALIDATION_ERROR,
                f"输入参数校验失败: {exc}",
                {"params": safe_params},
            ) from exc

        # 2. 构造查询参数（仅传非 None 字段）
        query_params: dict[str, str | int | float] = {}
        if inp.q is not None:
            query_params["q"] = inp.q
        if inp.name is not None:
            query_params["name"] = inp.name
        if inp.ownerName is not None:
            query_params["ownerName"] = inp.ownerName
        if inp.ownerPhone is not None:
            query_params["ownerPhone"] = inp.ownerPhone
        if inp.species is not None:
            query_params["species"] = inp.species
        if inp.doctor is not None:
            query_params["doctor"] = inp.doctor
        if inp.disease is not None:
            query_params["disease"] = inp.disease
        if inp.status is not None:
            query_params["status"] = inp.status
        if inp.min is not None:
            query_params["min"] = inp.min
        if inp.max is not None:
            query_params["max"] = inp.max
        if inp.sortBy is not None:
            query_params["sortBy"] = inp.sortBy
        if inp.order is not None:
            query_params["order"] = inp.order
        if inp.page is not None:
            query_params["page"] = inp.page
        if inp.pageSize is not None:
            query_params["pageSize"] = inp.pageSize

        # 3. 调用后端
        client = _get_client()
        data = await client.list_pets(query_params)

        # 4. 校验后端响应格式
        try:
            result = ListPetsSuccess(**data)
        except Exception as exc:
            raise ToolError(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                f"后端响应不符合数据模型: {exc}",
                {"url": "GET /api/v1/pets"},
            ) from exc

        duration_ms = int((time.monotonic() - start) * 1000)
        logger.info(
            "tool_call_complete",
            tool_name="list_pets",
            params=safe_params,
            status="ok",
            duration_ms=duration_ms,
            result_count=len(result.items),
        )
        return result

    except ToolError as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.warning(
            "tool_call_failed",
            tool_name="list_pets",
            params=safe_params,
            status="error",
            duration_ms=duration_ms,
            error_code=exc.code.value,
            error_message=exc.message,
        )
        # 返回错误信封作为工具结果（is_error=True 风格）
        raise ValueError(exc.to_json_string()) from exc

    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "tool_call_internal_error",
            tool_name="list_pets",
            params=safe_params,
            status="internal_error",
            duration_ms=duration_ms,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        raise ToolError(
            ErrorCode.INTERNAL_ERROR,
            f"内部错误: {exc}",
        ) from exc


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> Response:
    """MCP 服务自身的健康检查端点。"""
    return JSONResponse({"status": "ok", "service": "pet-hospital-mcp"})


def create_app():
    """创建 Starlette ASGI 应用。

    返回的 app 包含：
      - /mcp  : Streamable HTTP MCP 端点（无状态模式）
      - /health: 健康检查

    stateless_http=True 对应 MCP 2026-07-28 协议的无状态核心：
      - 不生成或追踪 Mcp-Session-Id
      - 不要求客户端先发送 initialize
      - 每个 POST 请求自包含可独立处理
    json_response=True 让简单工具调用直接返回 JSON，
    避免对短请求强制启用 SSE 流。
    """
    app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
    )
    return app
