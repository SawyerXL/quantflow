import uuid
from datetime import date, datetime

from pydantic import BaseModel


class BacktestCreate(BaseModel):
    name: str
    ticker: str
    strategy_id: uuid.UUID | None = None
    data_source: str = "yahoo"
    start_date: date
    end_date: date
    initial_capital: float = 10000.0
    config: dict = {}


class BacktestResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    strategy_id: uuid.UUID | None = None
    name: str
    ticker: str
    data_source: str
    start_date: date
    end_date: date
    initial_capital: float
    status: str
    total_return: float | None = None
    annual_return: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    win_rate: float | None = None
    total_trades: int | None = None
    profit_factor: float | None = None
    result_data: dict | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class BacktestListResponse(BaseModel):
    id: uuid.UUID
    name: str
    ticker: str
    data_source: str
    status: str
    total_return: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
