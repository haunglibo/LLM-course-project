"""统一错误结构。

所有工具调用失败都返回形如：
    {"error": {"code": "ERROR_CODE", "message": "...", "details": {...}}}
的结构，不向客户端暴露 SDK / HTTPX / Pydantic 堆栈。
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """错误码枚举。"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    BACKEND_TIMEOUT = "BACKEND_TIMEOUT"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    BACKEND_API_ERROR = "BACKEND_API_ERROR"
    BACKEND_INVALID_RESPONSE = "BACKEND_INVALID_RESPONSE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorBody(BaseModel):
    """错误体。"""

    code: str = Field(description="错误码")
    message: str = Field(description="可读错误信息")
    details: dict[str, Any] | None = Field(default=None, description="补充细节")


class ErrorEnvelope(BaseModel):
    """错误响应信封。"""

    error: ErrorBody


class ToolError(Exception):
    """工具内部异常，携带结构化错误信息。

    被工具捕获后转换为 MCP 工具错误返回给客户端。
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)

    def to_envelope(self) -> dict[str, Any]:
        """生成统一错误信封 dict。"""
        envelope = ErrorEnvelope(
            error=ErrorBody(
                code=self.code.value,
                message=self.message,
                details=self.details,
            )
        )
        return envelope.model_dump()

    def to_json_string(self) -> str:
        """生成统一错误信封 JSON 字符串（工具返回内容）。"""
        import json

        return json.dumps(self.to_envelope(), ensure_ascii=False)
