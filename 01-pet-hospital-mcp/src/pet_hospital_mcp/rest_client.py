"""Go REST API 客户端。

负责与上游 Go 宠物医院服务通信：
  - 超时控制
  - 有限重试
  - 统一异常映射
"""

from __future__ import annotations

import httpx

from .config import Settings
from .errors import ErrorCode, ToolError


class PetHospitalClient:
    """异步 HTTP 客户端，封装对 Go REST API 的调用。"""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._base_url = settings.pet_hospital_base_url.rstrip("/")
        self._timeout = settings.backend_timeout_seconds
        self._max_retries = settings.backend_max_retries
        self._transport = transport  # 测试时注入 MockTransport

    async def list_pets(self, params: dict[str, str | int | float]) -> dict:
        """GET /api/v1/pets

        Args:
            params: 已校验的查询参数字典（值均为 str/int/float）。

        Returns:
            Go API 成功响应中的 data 字段（dict）。

        Raises:
            ToolError: 后端超时、不可达、HTTP 错误或响应格式异常。
        """
        url = f"{self._base_url}/api/v1/pets"
        return await self._get_with_retry(url, params)

    async def health_check(self) -> dict:
        """GET /health — 供 MCP /health 端点探活上游。"""
        url = f"{self._base_url}/health"
        return await self._get_with_retry(url, {})

    async def _get_with_retry(
        self, url: str, params: dict[str, str | int | float]
    ) -> dict:
        """带超时和有限重试的 GET 请求。"""
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout, transport=self._transport
                ) as client:
                    resp = await client.get(url, params=params)
                return self._parse_response(resp, url)
            except ToolError:
                raise  # 响应解析错误直接抛出，不重试
            except httpx.TimeoutException as exc:
                last_exc = exc
                continue
            except httpx.ConnectError as exc:
                last_exc = exc
                continue
            except httpx.HTTPError as exc:
                last_exc = exc
                break  # 非 transient 错误，不重试
            except Exception as exc:
                last_exc = exc
                break

        # 所有重试耗尽后映射为 ToolError
        if isinstance(last_exc, httpx.TimeoutException):
            raise ToolError(
                ErrorCode.BACKEND_TIMEOUT,
                f"后端请求超时: {last_exc}",
                {"url": url, "timeout_seconds": self._timeout},
            )
        if isinstance(last_exc, httpx.ConnectError):
            raise ToolError(
                ErrorCode.BACKEND_UNAVAILABLE,
                f"无法连接后端服务: {last_exc}",
                {"url": url},
            )
        if isinstance(last_exc, httpx.HTTPError):
            raise ToolError(
                ErrorCode.BACKEND_API_ERROR,
                f"后端 HTTP 错误: {last_exc}",
                {"url": url},
            )
        raise ToolError(
            ErrorCode.INTERNAL_ERROR,
            f"内部错误: {last_exc}",
            {"url": url},
        )

    def _parse_response(self, resp: httpx.Response, url: str) -> dict:
        """解析 Go REST API 响应。

        Go 成功响应信封:
            {"code": 200, "message": "ok", "data": {...}, "time": "..."}
        """
        if resp.status_code >= 500:
            raise ToolError(
                ErrorCode.BACKEND_API_ERROR,
                f"后端返回 {resp.status_code}",
                {"url": url, "status_code": resp.status_code},
            )
        if resp.status_code >= 400:
            # 4xx: 尝试解析 body 中的 message
            try:
                body = resp.json()
                msg = body.get("message", resp.text)
            except Exception:
                msg = resp.text
            raise ToolError(
                ErrorCode.BACKEND_API_ERROR,
                f"后端返回 {resp.status_code}: {msg}",
                {"url": url, "status_code": resp.status_code},
            )

        try:
            body = resp.json()
        except Exception as exc:
            raise ToolError(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                f"后端响应不是有效 JSON: {exc}",
                {"url": url},
            ) from exc

        if not isinstance(body, dict):
            raise ToolError(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                f"后端响应不是 JSON 对象: {type(body).__name__}",
                {"url": url},
            )

        data = body.get("data")
        if data is None:
            raise ToolError(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                "后端响应缺少 data 字段",
                {"url": url},
            )
        if not isinstance(data, dict):
            raise ToolError(
                ErrorCode.BACKEND_INVALID_RESPONSE,
                f"后端 data 字段不是 JSON 对象: {type(data).__name__}",
                {"url": url},
            )

        return data
