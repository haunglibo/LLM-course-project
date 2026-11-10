"""MCP 服务测试。

使用 SDK 2.x 的 in-memory Client 测试：
  - 工具注册、工具名和 JSON Schema
  - 无状态连接流程（不发送 initialize / 不要求 Mcp-Session-Id）
  - /health 端点
  - 工具可通过 MCP 端点被发现和调用
"""

import json
from unittest.mock import AsyncMock, patch

import pytest
from mcp import Client

from pet_hospital_mcp import server
from pet_hospital_mcp.errors import ErrorCode, ToolError


# ---------------------------------------------------------------------------
# Mock 后端客户端
# ---------------------------------------------------------------------------


def _mock_backend_client(data: dict) -> AsyncMock:
    """创建返回指定 data 的 mock 后端客户端。"""
    mock = AsyncMock()
    mock.list_pets = AsyncMock(return_value=data)
    return mock


# ---------------------------------------------------------------------------
# 工具注册 / Schema 测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_registered():
    """6. 工具注册确认：list_pets 已注册。"""
    async with Client(server.mcp) as client:
        result = await client.list_tools()
    tool_names = [t.name for t in result.tools]
    assert "list_pets" in tool_names


@pytest.mark.asyncio
async def test_tool_has_input_schema():
    """6. 工具 JSON Schema 确认。"""
    async with Client(server.mcp) as client:
        result = await client.list_tools()
    tool = [t for t in result.tools if t.name == "list_pets"][0]
    assert tool.input_schema is not None
    assert tool.input_schema["type"] == "object"
    props = tool.input_schema["properties"]
    expected = {
        "q", "name", "ownerName", "ownerPhone", "species",
        "doctor", "disease", "status", "min", "max",
        "sortBy", "order", "page", "pageSize",
    }
    assert expected.issubset(set(props.keys()))


@pytest.mark.asyncio
async def test_tool_has_output_schema():
    """6. 工具 output_schema 确认。"""
    async with Client(server.mcp) as client:
        result = await client.list_tools()
    tool = [t for t in result.tools if t.name == "list_pets"][0]
    assert tool.output_schema is not None


@pytest.mark.asyncio
async def test_tool_description_present():
    """6. 工具描述确认。"""
    async with Client(server.mcp) as client:
        result = await client.list_tools()
    tool = [t for t in result.tools if t.name == "list_pets"][0]
    assert tool.description is not None
    assert "查询宠物档案列表" in tool.description


# ---------------------------------------------------------------------------
# 正常调用测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_pets_call_success(sample_list_response):
    """1. 正常调用：通过 in-memory Client 调用 list_pets。"""
    backend_data = sample_list_response["data"]
    mock_client = _mock_backend_client(backend_data)

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {
                "species": "犬", "page": 1, "pageSize": 10,
            })

    assert result.is_error is False
    assert result.structured_content is not None
    sc = result.structured_content
    assert sc["total"] == 1
    assert sc["page"] == 1
    assert len(sc["items"]) == 1
    assert sc["items"][0]["id"] == "PET-000001"


@pytest.mark.asyncio
async def test_list_pets_all_params_forwarded(sample_list_response):
    """1. 确认全部参数被转发到后端。"""
    backend_data = sample_list_response["data"]
    mock_client = _mock_backend_client(backend_data)

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            await client.call_tool("list_pets", {
                "q": "肠胃炎", "name": "旺财", "ownerName": "张三",
                "ownerPhone": "13800001111", "species": "犬",
                "doctor": "李医生", "disease": "肠胃炎",
                "status": "待就诊", "min": 100, "max": 5000,
                "sortBy": "totalCost", "order": "desc",
                "page": 2, "pageSize": 50,
            })

    mock_client.list_pets.assert_called_once()
    call_args = mock_client.list_pets.call_args[0][0]
    assert call_args["q"] == "肠胃炎"
    assert call_args["species"] == "犬"
    assert call_args["page"] == 2
    assert call_args["pageSize"] == 50


@pytest.mark.asyncio
async def test_list_pets_empty_result(empty_list_response):
    """空列表正常返回。"""
    backend_data = empty_list_response["data"]
    mock_client = _mock_backend_client(backend_data)

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {})

    assert result.is_error is False
    assert result.structured_content["total"] == 0
    assert result.structured_content["items"] == []


@pytest.mark.asyncio
async def test_list_pets_no_args(sample_list_response):
    """不传任何参数，正常调用。"""
    backend_data = sample_list_response["data"]
    mock_client = _mock_backend_client(backend_data)

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {})

    assert result.is_error is False
    mock_client.list_pets.assert_called_once_with({})


# ---------------------------------------------------------------------------
# 错误处理测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_pets_validation_error_invalid_species():
    """2. 输入校验失败：无效 species。"""
    mock_client = _mock_backend_client({})

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {
                "species": "恐龙",
            })

    assert result.is_error is True
    assert mock_client.list_pets.called is False


@pytest.mark.asyncio
async def test_list_pets_validation_error_page_zero():
    """2. 输入校验失败：page=0。"""
    mock_client = _mock_backend_client({})

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {
                "page": 0,
            })

    assert result.is_error is True
    assert mock_client.list_pets.called is False


@pytest.mark.asyncio
async def test_list_pets_validation_error_min_greater_max():
    """2. 输入校验失败：min > max。"""
    mock_client = _mock_backend_client({})

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {
                "min": 500, "max": 100,
            })

    assert result.is_error is True
    assert mock_client.list_pets.called is False


@pytest.mark.asyncio
async def test_list_pets_validation_error_pagesize_exceeds():
    """2. 输入校验失败：pageSize > 500。"""
    mock_client = _mock_backend_client({})

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {
                "pageSize": 501,
            })

    assert result.is_error is True


@pytest.mark.asyncio
async def test_list_pets_backend_4xx():
    """3. 后端 4xx 错误。"""
    mock_client = AsyncMock()
    mock_client.list_pets = AsyncMock(
        side_effect=ToolError(
            ErrorCode.BACKEND_API_ERROR,
            "后端返回 400: 参数错误",
        )
    )

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {"page": 1})

    assert result.is_error is True
    text = result.content[0].text
    assert "Traceback" not in text


@pytest.mark.asyncio
async def test_list_pets_backend_timeout():
    """4. 后端超时。"""
    mock_client = AsyncMock()
    mock_client.list_pets = AsyncMock(
        side_effect=ToolError(
            ErrorCode.BACKEND_TIMEOUT,
            "后端请求超时",
        )
    )

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {"page": 1})

    assert result.is_error is True


@pytest.mark.asyncio
async def test_list_pets_backend_unavailable():
    """4. 后端不可达。"""
    mock_client = AsyncMock()
    mock_client.list_pets = AsyncMock(
        side_effect=ToolError(
            ErrorCode.BACKEND_UNAVAILABLE,
            "无法连接后端服务",
        )
    )

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {"page": 1})

    assert result.is_error is True


@pytest.mark.asyncio
async def test_list_pets_backend_invalid_response():
    """5. 后端返回非法 JSON。"""
    mock_client = AsyncMock()
    mock_client.list_pets = AsyncMock(
        side_effect=ToolError(
            ErrorCode.BACKEND_INVALID_RESPONSE,
            "后端响应不是有效 JSON",
        )
    )

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {"page": 1})

    assert result.is_error is True


@pytest.mark.asyncio
async def test_list_pets_backend_data_model_mismatch():
    """5. 后端数据模型不匹配。"""
    mock_client = AsyncMock()
    mock_client.list_pets = AsyncMock(
        side_effect=ToolError(
            ErrorCode.BACKEND_INVALID_RESPONSE,
            "后端响应不符合数据模型",
        )
    )

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {"page": 1})

    assert result.is_error is True


@pytest.mark.asyncio
async def test_list_pets_internal_error():
    """内部错误不暴露堆栈。"""
    mock_client = AsyncMock()
    mock_client.list_pets = AsyncMock(
        side_effect=ToolError(
            ErrorCode.INTERNAL_ERROR,
            "内部错误",
        )
    )

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.call_tool("list_pets", {"page": 1})

    assert result.is_error is True
    text = result.content[0].text
    assert "Traceback" not in text
    assert "httpx" not in text.lower()
    assert "pydantic" not in text.lower()


# ---------------------------------------------------------------------------
# SDK 2.x 无状态连接流程测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_initialize_required(sample_list_response):
    """7. 不发送旧 initialize 握手。

    SDK 2.x 的 in-memory Client 连接时不调用 initialize。
    如果成功连接并返回工具列表，说明不需要 initialize。
    """
    mock_client = _mock_backend_client(sample_list_response["data"])

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            result = await client.list_tools()
    assert len(result.tools) > 0


@pytest.mark.asyncio
async def test_tool_discoverable_and_callable(sample_list_response):
    """7. 验证工具可通过 MCP 端点被发现和调用。"""
    mock_client = _mock_backend_client(sample_list_response["data"])

    with patch.object(server, "_get_client", return_value=mock_client):
        async with Client(server.mcp) as client:
            # 发现
            result = await client.list_tools()
            tool = [t for t in result.tools if t.name == "list_pets"][0]
            assert tool is not None

            # 调用
            call_result = await client.call_tool("list_pets", {
                "species": "犬", "page": 1,
            })

    assert call_result.is_error is False
    assert call_result.structured_content is not None


# ---------------------------------------------------------------------------
# /health 端点测试
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint():
    """7. 验证 /health 端点。"""
    from starlette.testclient import TestClient

    app = server.create_app()
    with TestClient(app) as test_client:
        resp = test_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "pet-hospital-mcp"


@pytest.mark.asyncio
async def test_mcp_endpoint_accessible():
    """7. 验证 /mcp 端点存在（Streamable HTTP）。"""
    from starlette.testclient import TestClient

    app = server.create_app()
    with TestClient(app) as test_client:
        resp = test_client.get("/mcp")
        assert resp.status_code != 404
