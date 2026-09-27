"""purchaseエンドポイントのPydanticスキーマ（API契約のsource of truth）。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PurchaseCreateRequest(BaseModel):
    """購入物の新規作成リクエスト。"""

    name: str = Field(min_length=1, max_length=50)
    category: str = Field(min_length=1, max_length=30)
    speed: int = Field(ge=0, le=100_000, strict=True, description="消費スピード")
    stock: int = Field(ge=0, le=100_000, strict=True, description="現在の在庫")
    is_temporary: bool = False

    @field_validator("name", "category")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("空白だけの入力はできません")
        return value


class PurchasePutRequest(BaseModel):
    """購入物の更新リクエスト。"""

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    speed: float = Field(gt=0, description="消費スピード")
    stock: float = Field(ge=0, description="現在の在庫")
    is_temporary: bool = False


class PurchaseResponse(BaseModel):
    """購入物のレスポンス表現。"""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str
    speed: float
    stock: float
    is_temporary: bool
    created_at: datetime
    updated_at: datetime
