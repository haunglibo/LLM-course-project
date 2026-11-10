"""结构化日志配置。

使用 structlog 输出 JSON 格式日志，包含：
  timestamp, tool_name, params, status, duration_ms
同时对敏感字段（ownerPhone, ownerAddr, chipNo 及其 snake_case 变体）递归脱敏。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import structlog

# 需要脱敏的字段名（大小写不敏感匹配 phone / addr / chip）
_SENSITIVE_PATTERNS = re.compile(r"(phone|addr|chipno|chip_no)", re.IGNORECASE)

_MASK = "***REDACTED***"


def _mask_value(value: Any) -> str:
    """将敏感值脱敏为固定掩码。"""
    return _MASK


def _redact(obj: Any) -> Any:
    """递归脱敏：对 dict 中匹配敏感模式的 key 做掩码。"""
    if isinstance(obj, dict):
        return {
            k: (_mask_value(v) if _SENSITIVE_PATTERNS.search(str(k)) else _redact(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_redact(item) for item in obj]
    return obj


def redact_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    """对外暴露的脱敏入口，供工具日志使用。"""
    if params is None:
        return None
    return _redact(params)


def configure_logging(level: str = "INFO") -> None:
    """配置 structlog + 标准库 logging。"""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            _json_renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def _json_renderer(logger: Any, name: str, event_dict: dict[str, Any]) -> str:
    """将事件字典渲染为 JSON 字符串，递归脱敏敏感字段。"""
    redacted = _redact(event_dict)
    return json.dumps(redacted, ensure_ascii=False, default=str)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """获取一个绑定了名称的 structlog logger。"""
    return structlog.get_logger(name)
