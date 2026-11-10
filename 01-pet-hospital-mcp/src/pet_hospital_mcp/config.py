"""配置模块：从环境变量读取运行参数。"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """运行配置，全部通过环境变量注入。"""

    mcp_host: str
    mcp_port: int
    pet_hospital_base_url: str
    backend_timeout_seconds: float
    backend_max_retries: int

    @property
    def mcp_url(self) -> str:
        """MCP 端点完整 URL。"""
        return f"http://{self.mcp_host}:{self.mcp_port}/mcp"


def load_settings() -> Settings:
    """从环境变量加载配置，应用默认值。"""
    return Settings(
        mcp_host=os.environ.get("MCP_HOST", "127.0.0.1"),
        mcp_port=int(os.environ.get("MCP_PORT", "8000")),
        pet_hospital_base_url=os.environ.get(
            "PET_HOSPITAL_BASE_URL", "http://127.0.0.1:8080"
        ),
        backend_timeout_seconds=float(os.environ.get("BACKEND_TIMEOUT_SECONDS", "10.0")),
        backend_max_retries=int(os.environ.get("BACKEND_MAX_RETRIES", "2")),
    )
