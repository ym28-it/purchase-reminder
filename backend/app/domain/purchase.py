from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass()
class Purchase:
    id: UUID
    user_id: str
    name: str
    category: str
    speed: float
    stock: float
    is_temporary: bool
    created_at: datetime
    updated_at: datetime
