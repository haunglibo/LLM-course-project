"""AnythingLLM MCP Server (MVP).

使用 MCP 2026-07-28 协议 + Python SDK 2.x 的 MCPServer，
以无状态 Streamable HTTP 暴露一个工具：
    ask_first_workspace(message) -> str
向本机 AnythingLLM 第一个工作区提问，返回 AI 回答。

环境变量：
    ANYTHINGLLM_BASE_URL  默认 http://localhost:3001
    ANYTHINGLLM_API_KEY   必填
    MCP_HOST               默认 127.0.0.1
    MCP_PORT               默认 8765
"""
from __future__ import annotations

import os
import uuid

import httpx
from mcp.server import MCPServer

# ---------- 配置 ----------
BASE_URL = os.environ.get("ANYTHINGLLM_BASE_URL", "http://localhost:3001").rstrip("/")
API_KEY = os.environ.get("ANYTHINGLLM_API_KEY", "")
HOST = os.environ.get("MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("MCP_PORT", "8765"))
TIMEOUT = float(os.environ.get("ANYTHINGLLM_TIMEOUT", "120"))

mcp = MCPServer("anythingllm-mcp")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


async def _first_workspace_slug(client: httpx.AsyncClient) -> str:
    """获取第一个工作区的 slug（运行时动态取，避免硬编码）。"""
    resp = await client.get(f"{BASE_URL}/api/v1/workspaces", headers=_headers())
    resp.raise_for_status()
    data = resp.json()
    workspaces = data.get("workspaces") or data
    if not workspaces:
        raise RuntimeError("AnythingLLM 中没有工作区")
    slug = workspaces[0].get("slug")
    if not slug:
        raise RuntimeError(f"工作区缺少 slug 字段: {workspaces[0]}")
    return slug


@mcp.tool()
async def ask_first_workspace(message: str) -> str:
    """向 AnythingLLM 第一个工作区提问，返回 AI 的回答文本。

    参数：
        message  要向工作区提的问题（中文/英文均可）

    返回：
        AI 回答文本。若上游 LLM 调用失败，返回后端的错误描述。

    适用场景：
        需要利用 AnythingLLM 中已嵌入的文档库做检索增强问答时使用。
    """
    if not API_KEY:
        raise ValueError("ANYTHINGLLM_API_KEY 未配置")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        slug = await _first_workspace_slug(client)
        body = {
            "message": message,
            "mode": "automatic",
            "sessionId": f"mcp-{uuid.uuid4().hex[:8]}",
        }
        resp = await client.post(
            f"{BASE_URL}/api/v1/workspace/{slug}/chat",
            headers=_headers(),
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("error"):
        return f"[AnythingLLM 错误] {data['error']}"
    text = data.get("textResponse", "").strip()
    if not text:
        return f"[AnythingLLM 返回空回答] 原始响应: {data}"
    return text


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    from starlette.responses import JSONResponse
    return JSONResponse({"status": "ok", "service": "anythingllm-mcp"})


def main() -> None:
    print(f"AnythingLLM MCP 启动中...")
    print(f"  MCP 端点:        http://{HOST}:{PORT}/mcp")
    print(f"  健康检查:        http://{HOST}:{PORT}/health")
    print(f"  AnythingLLM:     {BASE_URL}")
    print(f"  API Key 已配置:  {bool(API_KEY)}")
    mcp.run(
        transport="streamable-http",
        host=HOST,
        port=PORT,
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()
