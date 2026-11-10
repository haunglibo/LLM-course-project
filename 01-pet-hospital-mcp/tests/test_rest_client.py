"""REST 客户端测试。

使用 httpx.MockTransport 模拟 Go REST API，禁止访问真实服务。
"""

import httpx
import pytest

from pet_hospital_mcp.config import Settings
from pet_hospital_mcp.errors import ErrorCode, ToolError
from pet_hospital_mcp.rest_client import PetHospitalClient


def _make_client(transport: httpx.MockTransport) -> PetHospitalClient:
    """构造使用指定 transport 的客户端。"""
    settings = Settings(
        mcp_host="127.0.0.1",
        mcp_port=8000,
        pet_hospital_base_url="http://127.0.0.1:8080",
        backend_timeout_seconds=5.0,
        backend_max_retries=1,
    )
    return PetHospitalClient(settings, transport=transport)


@pytest.mark.asyncio
async def test_list_pets_normal(sample_list_response):
    """1. 正常调用：确认请求路径和参数转发。"""
    captured_params = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_params.update(dict(request.url.params))
        return httpx.Response(200, json=sample_list_response)

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    result = await client.list_pets({
        "species": "犬", "page": 1, "pageSize": 10,
        "sortBy": "totalCost", "order": "desc",
    })

    assert result["total"] == 1
    assert captured_params["species"] == "犬"
    assert captured_params["page"] == "1"
    assert captured_params["pageSize"] == "10"
    assert captured_params["sortBy"] == "totalCost"
    assert captured_params["order"] == "desc"


@pytest.mark.asyncio
async def test_list_pets_all_params_forwarded(sample_list_response):
    """确认全部 14 个参数都被转发。"""
    captured_params = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_params.update(dict(request.url.params))
        return httpx.Response(200, json=sample_list_response)

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    await client.list_pets({
        "q": "肠胃炎", "name": "旺财", "ownerName": "张三",
        "ownerPhone": "13800001111", "species": "犬", "doctor": "李医生",
        "disease": "肠胃炎", "status": "待就诊", "min": 100, "max": 5000,
        "sortBy": "name", "order": "asc", "page": 2, "pageSize": 50,
    })

    expected_keys = {
        "q", "name", "ownerName", "ownerPhone", "species", "doctor",
        "disease", "status", "min", "max", "sortBy", "order", "page", "pageSize",
    }
    assert set(captured_params.keys()) == expected_keys


@pytest.mark.asyncio
async def test_list_pets_4xx_error():
    """3. Go REST API 返回 4xx。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"code": 400, "message": "参数错误"})

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    with pytest.raises(ToolError) as exc_info:
        await client.list_pets({"page": 1})

    assert exc_info.value.code == ErrorCode.BACKEND_API_ERROR
    assert "400" in exc_info.value.message


@pytest.mark.asyncio
async def test_list_pets_5xx_error():
    """3. Go REST API 返回 5xx。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    with pytest.raises(ToolError) as exc_info:
        await client.list_pets({"page": 1})

    assert exc_info.value.code == ErrorCode.BACKEND_API_ERROR
    assert "500" in exc_info.value.message


@pytest.mark.asyncio
async def test_list_pets_timeout():
    """4. 超时异常。"""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("simulated timeout")

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    with pytest.raises(ToolError) as exc_info:
        await client.list_pets({"page": 1})

    assert exc_info.value.code == ErrorCode.BACKEND_TIMEOUT


@pytest.mark.asyncio
async def test_list_pets_connect_error():
    """4. 连接异常。"""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    with pytest.raises(ToolError) as exc_info:
        await client.list_pets({"page": 1})

    assert exc_info.value.code == ErrorCode.BACKEND_UNAVAILABLE


@pytest.mark.asyncio
async def test_list_pets_invalid_json():
    """5. 后端返回非法 JSON。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not json {{{")

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    with pytest.raises(ToolError) as exc_info:
        await client.list_pets({"page": 1})

    assert exc_info.value.code == ErrorCode.BACKEND_INVALID_RESPONSE


@pytest.mark.asyncio
async def test_list_pets_missing_data_field():
    """5. 后端响应缺少 data 字段。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 200, "message": "ok"})

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    with pytest.raises(ToolError) as exc_info:
        await client.list_pets({"page": 1})

    assert exc_info.value.code == ErrorCode.BACKEND_INVALID_RESPONSE


@pytest.mark.asyncio
async def test_list_pets_data_not_dict():
    """5. 后端 data 字段不是对象。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"code": 200, "data": [1, 2, 3]})

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    with pytest.raises(ToolError) as exc_info:
        await client.list_pets({"page": 1})

    assert exc_info.value.code == ErrorCode.BACKEND_INVALID_RESPONSE


@pytest.mark.asyncio
async def test_list_pets_empty_list(empty_list_response):
    """空列表正常返回。"""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=empty_list_response)

    transport = httpx.MockTransport(handler)
    client = _make_client(transport)

    result = await client.list_pets({"page": 1})
    assert result["total"] == 0
    assert result["items"] == []
