"""共享测试 fixtures。"""

import sys
from pathlib import Path

import pytest

# 将 src 目录加入 sys.path，确保无需安装即可测试
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))


@pytest.fixture
def sample_pet_data():
    """Go REST API 单条宠物档案数据。"""
    return {
        "id": "PET-000001",
        "name": "旺财",
        "species": "犬",
        "breed": "金毛",
        "gender": "公",
        "ageMonths": 36,
        "color": "金色",
        "chipNo": "CHIP-001",
        "ownerName": "张三",
        "ownerPhone": "13800001111",
        "ownerAddr": "北京市朝阳区",
        "doctor": "李医生",
        "disease": "急性肠胃炎",
        "status": "待就诊",
        "allergy": "无",
        "note": "",
        "records": [
            {
                "id": "MR-1",
                "visitDate": "2025-01-01",
                "doctor": "李医生",
                "diagnosis": "急性肠胃炎",
                "symptoms": "呕吐腹泻",
                "treatment": "补液消炎",
                "prescription": ["阿莫西林"],
                "charge": 380,
                "createdAt": "2025-01-01T10:00:00+08:00",
            }
        ],
        "charges": [
            {
                "id": "CH-1",
                "item": "血常规检查",
                "category": "检查",
                "amount": 180,
                "doctor": "李医生",
                "date": "2025-01-01",
            }
        ],
        "totalCost": 560.0,
        "visitCount": 1,
        "createdAt": "2025-01-01T10:00:00+08:00",
        "updatedAt": "2025-01-01T10:00:00+08:00",
    }


@pytest.fixture
def sample_list_response(sample_pet_data):
    """Go REST API GET /api/v1/pets 成功响应。"""
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "items": [sample_pet_data],
            "total": 1,
            "page": 1,
            "pageSize": 20,
            "totalPages": 1,
            "totalCost": 560.0,
        },
        "time": "2025-01-01T10:00:00+08:00",
    }


@pytest.fixture
def empty_list_response():
    """Go REST API 空列表响应。"""
    return {
        "code": 200,
        "message": "ok",
        "data": {
            "items": [],
            "total": 0,
            "page": 1,
            "pageSize": 20,
            "totalPages": 0,
            "totalCost": 0.0,
        },
        "time": "2025-01-01T10:00:00+08:00",
    }
