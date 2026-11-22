"""purchaseエンドポイントのPydanticスキーマ（API契約のsource of truth）。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PurchaseCreateRequest(BaseModel):
    """購入物の新規作成リクエスト。"""

    name: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=30)
    unit: str = Field(min_length=1, max_length=10, description="数量の単位")
    days_per_unit: int = Field(ge=0, le=365, strict=True, description="1単位を使い切る日数")
    buffer_days: int = Field(ge=0, le=30, strict=True, description="余裕日数")
    stock: int = Field(ge=0, le=100_000, strict=True, description="現在の在庫")
    is_temporary: bool = Field(strict=True, description="一時的な購入（必須）")

    @field_validator("name", "category", "unit")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("空白だけの入力はできません")
        return value


class PurchasePutRequest(BaseModel):
    """購入物の更新リクエスト。"""

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    days_per_unit: float = Field(gt=0, description="1単位を使い切る日数")
    stock: float = Field(ge=0, description="現在の在庫")
    is_temporary: bool = False


class PurchaseResponse(BaseModel):
    """購入物のレスポンス表現。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str
    unit: str
    days_per_unit: float
    buffer_days: int
    stock: float
    is_temporary: bool
    stock_counted_at: datetime
    created_at: datetime
    updated_at: datetime
