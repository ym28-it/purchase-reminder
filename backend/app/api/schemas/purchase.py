"""purchaseエンドポイントのPydanticスキーマ（API契約のsource of truth）。"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PurchaseCreateRequest(BaseModel):
    """購入物の新規作成リクエスト。"""

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
