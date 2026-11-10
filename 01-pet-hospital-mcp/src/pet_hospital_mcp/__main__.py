"""MCP 服务入口点。

用法：
    python -m pet_hospital_mcp
    python -m pet_hospital_mcp --host 0.0.0.0 --port 9000

环境变量：
    MCP_HOST                  监听地址（默认 127.0.0.1）
    MCP_PORT                  监听端口（默认 8000）
    PET_HOSPITAL_BASE_URL     Go REST API 地址（默认 http://127.0.0.1:8080）
"""

from __future__ import annotations

import sys

from .config import load_settings
from .logging_config import configure_logging
from .server import mcp


def main() -> None:
    """启动 MCP 服务。"""
    settings = load_settings()
    configure_logging()

    print(f"宠物医院 MCP 服务启动中...")
    print(f"  MCP 端点:     {settings.mcp_url}")
    print(f"  Go API 地址:  {settings.pet_hospital_base_url}")
    print(f"  健康检查:     http://{settings.mcp_host}:{settings.mcp_port}/health")
    print()

    mcp.run(
        transport="streamable-http",
        host=settings.mcp_host,
        port=settings.mcp_port,
        stateless_http=True,   # MCP 2026-07-28 协议无状态核心
        json_response=True,    # 简单工具调用直接返回 JSON
    )


if __name__ == "__main__":
    main()
