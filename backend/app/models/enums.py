import enum


def enum_value(obj) -> str:
    """Get the string value from an enum or string. Safe for any case."""
    if isinstance(obj, enum.Enum):
        return obj.value
    return str(obj)


class Plan(str, enum.Enum):
    free = "free"
    pro = "pro"
    quant = "quant"


class StrategyType(str, enum.Enum):
    ma_cross = "ma_cross"
    rsi = "rsi"
    bollinger = "bollinger"
    custom = "custom"


class DataSource(str, enum.Enum):
    upload = "upload"
    yahoo = "yahoo"
    binance = "binance"


class BacktestStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
