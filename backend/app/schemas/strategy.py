import uuid
from datetime import datetime

from pydantic import BaseModel


class StrategyCreate(BaseModel):
    name: str
    strategy_type: str
    config: dict = {}
    is_public: bool = False


class StrategyUpdate(BaseModel):
    name: str | None = None
    config: dict | None = None
    is_public: bool | None = None


class StrategyResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    strategy_type: str
    config: dict
    is_public: bool
    created_at: datetime

    model_config = {"from_attributes": True}
