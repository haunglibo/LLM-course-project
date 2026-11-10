"""list_pets 工具：查询宠物档案列表。

严格适配 Go REST API 的 GET /api/v1/pets，支持全部 14 个查询参数。
使用 Pydantic 定义输入模型、成功输出模型和错误输出模型。
"""

from __future__ import annotations


import math
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# 枚举：从 Go API 的 /api/v1/meta 端点获取的真实允许值
# ---------------------------------------------------------------------------

SpeciesType = Literal[
    "犬", "猫", "兔", "鸟", "仓鼠", "爬宠", "其他"
]

StatusType = Literal[
    "待就诊", "就诊中", "住院中", "已康复", "慢性病随访"
]

SortByType = Literal[
    "id", "name", "ownerName", "species", "doctor",
    "disease", "status", "totalCost", "visitCount",
    "createdAt", "updatedAt",
]

OrderType = Literal["asc", "desc"]


# ---------------------------------------------------------------------------
# 输入模型
# ---------------------------------------------------------------------------


class ListPetsInput(BaseModel):
    """list_pets 工具输入参数。

    所有字段均可选，未传的字段不会转发给后端。
    species / status / sortBy / order 使用真实后端允许值。
    page >= 1, 1 <= pageSize <= 500, min/max 非负, min <= max。
    """

    q: str | None = Field(default=None, description="全文检索关键词（跨字段，空格分词 AND）")
    name: str | None = Field(default=None, description="宠物姓名（模糊匹配）")
    ownerName: str | None = Field(default=None, description="主人姓名（模糊匹配）")
    ownerPhone: str | None = Field(default=None, description="主人电话（模糊匹配）")
    species: SpeciesType | None = Field(default=None, description="宠物种类（精确匹配）")
    doctor: str | None = Field(default=None, description="主治医生（模糊匹配）")
    disease: str | None = Field(default=None, description="疾病（模糊匹配）")
    status: StatusType | None = Field(default=None, description="就诊状态（精确匹配）")
    min: float | None = Field(default=None, ge=0, description="最低总花费")
    max: float | None = Field(default=None, ge=0, description="最高总花费")
    sortBy: SortByType | None = Field(default=None, description="排序字段")
    order: OrderType | None = Field(default=None, description="排序方向")
    page: int | None = Field(default=None, ge=1, description="页码，从 1 开始")
    pageSize: int | None = Field(
        default=None, ge=1, le=500, description="每页条数，1-500"
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _check_min_max(self) -> ListPetsInput:
        """确保 min <= max，拒绝 NaN / Infinity。"""
        for field_name in ("min", "max"):
            val = getattr(self, field_name)
            if val is not None:
                if math.isnan(val):
                    raise ValueError(f"{field_name} 不能是 NaN")
                if math.isinf(val):
                    raise ValueError(f"{field_name} 不能是 Infinity")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min 不能大于 max")
        return self


# ---------------------------------------------------------------------------
# 输出模型：严格对应 Go API store.Result 结构
# ---------------------------------------------------------------------------


class MedicalRecord(BaseModel):
    """历史病历条目。"""

    id: str | None = Field(default=None)
    visitDate: str | None = Field(default=None)
    doctor: str | None = Field(default=None)
    diagnosis: str | None = Field(default=None)
    symptoms: str | None = Field(default=None)
    treatment: str | None = Field(default=None)
    prescription: list[str] | None = Field(default=None)
    weightKg: float | None = Field(default=None)
    temperature: float | None = Field(default=None)
    followUp: str | None = Field(default=None)
    charge: float | None = Field(default=None)
    createdAt: str | None = Field(default=None)

    model_config = {"extra": "allow"}


class Treatment(BaseModel):
    """消费明细条目。"""

    id: str | None = Field(default=None)
    item: str | None = Field(default=None)
    category: str | None = Field(default=None)
    amount: float | None = Field(default=None)
    doctor: str | None = Field(default=None)
    date: str | None = Field(default=None)
    note: str | None = Field(default=None)

    model_config = {"extra": "allow"}


class PetItem(BaseModel):
    """宠物档案。

    records / charges 可能为 null 或数组，使用 list | None 兼容。
    """

    id: str | None = Field(default=None)
    name: str | None = Field(default=None)
    species: str | None = Field(default=None)
    breed: str | None = Field(default=None)
    gender: str | None = Field(default=None)
    ageMonths: int | None = Field(default=None)
    color: str | None = Field(default=None)
    chipNo: str | None = Field(default=None)
    ownerName: str | None = Field(default=None)
    ownerPhone: str | None = Field(default=None)
    ownerAddr: str | None = Field(default=None)
    doctor: str | None = Field(default=None)
    disease: str | None = Field(default=None)
    status: str | None = Field(default=None)
    allergy: str | None = Field(default=None)
    note: str | None = Field(default=None)
    records: list[MedicalRecord] | None = Field(default=None)
    charges: list[Treatment] | None = Field(default=None)
    totalCost: float | None = Field(default=None)
    visitCount: int | None = Field(default=None)
    createdAt: str | None = Field(default=None)
    updatedAt: str | None = Field(default=None)

    model_config = {"extra": "allow"}


class ListPetsSuccess(BaseModel):
    """成功输出：对应 Go API data 字段。"""

    items: list[PetItem] = Field(description="宠物档案列表")
    total: int = Field(description="过滤后总条数")
    page: int = Field(description="当前页码")
    pageSize: int = Field(description="每页条数")
    totalPages: int = Field(description="总页数")
    totalCost: float = Field(description="结果集花费合计")

    model_config = {"extra": "allow"}


class ListPetsError(BaseModel):
    """错误输出：统一错误信封。"""

    error: dict = Field(description="错误信息，包含 code / message / details")
