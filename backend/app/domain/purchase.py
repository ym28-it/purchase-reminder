from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID


@dataclass()
class Purchase:
    id: UUID
    user_id: str
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


def apply_edit(
    current: Purchase,
    *,
    name: str,
    category: str,
    unit: str,
    days_per_unit: float,
    buffer_days: int,
    stock: float,
    is_temporary: bool,
    now: datetime,
) -> Purchase:
    """編集内容を``current``へ適用した新しい``Purchase``を返す。

    7項目はすべて引数の値で置き換え、``created_at``は``current``から引き継ぐ。
    在庫が変わったときだけ``stock_counted_at``を``now``へ更新する。
    """
    return replace(
        current,
        name=name,
        category=category,
        unit=unit,
        days_per_unit=days_per_unit,
        buffer_days=buffer_days,
        stock=stock,
        is_temporary=is_temporary,
        stock_counted_at=now if stock != current.stock else current.stock_counted_at,
        updated_at=now,
    )
