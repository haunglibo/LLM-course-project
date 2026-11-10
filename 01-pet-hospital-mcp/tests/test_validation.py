"""输入参数校验测试。

覆盖：
  - species / status / sortBy / order 枚举校验
  - page >= 1
  - 1 <= pageSize <= 500
  - min / max 非负
  - min <= max
  - 拒绝未知字段
  - 拒绝 NaN / Infinity
  - 拒绝类型不正确
"""

import math

import pytest
from pydantic import ValidationError

from pet_hospital_mcp.tools.list_pets import ListPetsInput


class TestSpeciesValidation:
    """species 枚举校验。"""

    def test_valid_species(self):
        for s in ["犬", "猫", "兔", "鸟", "仓鼠", "爬宠", "其他"]:
            inp = ListPetsInput(species=s)
            assert inp.species == s

    def test_invalid_species(self):
        with pytest.raises(ValidationError):
            ListPetsInput(species="恐龙")

    def test_none_species(self):
        inp = ListPetsInput()
        assert inp.species is None


class TestStatusValidation:
    """status 枚举校验。"""

    def test_valid_status(self):
        for s in ["待就诊", "就诊中", "住院中", "已康复", "慢性病随访"]:
            inp = ListPetsInput(status=s)
            assert inp.status == s

    def test_invalid_status(self):
        with pytest.raises(ValidationError):
            ListPetsInput(status="死亡")

    def test_none_status(self):
        inp = ListPetsInput()
        assert inp.status is None


class TestSortByValidation:
    """sortBy 枚举校验。"""

    def test_valid_sortby(self):
        for s in [
            "id", "name", "ownerName", "species", "doctor",
            "disease", "status", "totalCost", "visitCount",
            "createdAt", "updatedAt",
        ]:
            inp = ListPetsInput(sortBy=s)
            assert inp.sortBy == s

    def test_invalid_sortby(self):
        with pytest.raises(ValidationError):
            ListPetsInput(sortBy="random")


class TestOrderValidation:
    """order 枚举校验。"""

    def test_valid_order(self):
        inp1 = ListPetsInput(order="asc")
        inp2 = ListPetsInput(order="desc")
        assert inp1.order == "asc"
        assert inp2.order == "desc"

    def test_invalid_order(self):
        with pytest.raises(ValidationError):
            ListPetsInput(order="random")


class TestPageValidation:
    """page 校验。"""

    def test_valid_page(self):
        inp = ListPetsInput(page=1)
        assert inp.page == 1

    def test_page_zero(self):
        with pytest.raises(ValidationError):
            ListPetsInput(page=0)

    def test_page_negative(self):
        with pytest.raises(ValidationError):
            ListPetsInput(page=-1)


class TestPageSizeValidation:
    """pageSize 校验。"""

    def test_valid_pagesize(self):
        inp = ListPetsInput(pageSize=20)
        assert inp.pageSize == 20

    def test_pagesize_zero(self):
        with pytest.raises(ValidationError):
            ListPetsInput(pageSize=0)

    def test_pagesexceeds_max(self):
        with pytest.raises(ValidationError):
            ListPetsInput(pageSize=501)

    def test_pagesize_500(self):
        inp = ListPetsInput(pageSize=500)
        assert inp.pageSize == 500


class TestMinMaxValidation:
    """min / max 校验。"""

    def test_valid_min_max(self):
        inp = ListPetsInput(min=100, max=5000)
        assert inp.min == 100
        assert inp.max == 5000

    def test_negative_min(self):
        with pytest.raises(ValidationError):
            ListPetsInput(min=-1)

    def test_negative_max(self):
        with pytest.raises(ValidationError):
            ListPetsInput(max=-0.01)

    def test_min_greater_than_max(self):
        with pytest.raises(ValidationError):
            ListPetsInput(min=500, max=100)

    def test_min_equal_max(self):
        inp = ListPetsInput(min=100, max=100)
        assert inp.min == inp.max


class TestUnknownFields:
    """拒绝未知字段。"""

    def test_unknown_field_rejected(self):
        with pytest.raises(ValidationError):
            ListPetsInput(unknownParam="value")

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            ListPetsInput(extra=123)


class TestNaNAndInfinity:
    """拒绝 NaN / Infinity。"""

    def test_nan_min(self):
        with pytest.raises(ValidationError):
            ListPetsInput(min=float("nan"))

    def test_nan_max(self):
        with pytest.raises(ValidationError):
            ListPetsInput(max=float("nan"))

    def test_infinity_min(self):
        with pytest.raises(ValidationError):
            ListPetsInput(min=float("inf"))

    def test_infinity_max(self):
        with pytest.raises(ValidationError):
            ListPetsInput(max=float("inf"))


class TestWrongTypes:
    """拒绝类型不正确。"""

    def test_page_as_string(self):
        with pytest.raises(ValidationError):
            ListPetsInput(page="first")

    def test_pagesize_as_float(self):
        with pytest.raises(ValidationError):
            ListPetsInput(pageSize=1.5)

    def test_min_as_list(self):
        with pytest.raises(ValidationError):
            ListPetsInput(min=[100])
