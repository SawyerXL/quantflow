"""Strategy metadata — names, categories, parameter specs for frontend rendering."""

STRATEGY_CONFIGS = {
    # ── Trend Following ──
    "ma_cross": {
        "name": "MA Crossover", "category": "Trend Following",
        "description": "Fast MA crosses above slow MA triggers buy",
        "params": [
            {"key": "fast_period", "label": "Fast Period", "type": "int", "default": 10, "min": 2, "max": 50},
            {"key": "slow_period", "label": "Slow Period", "type": "int", "default": 30, "min": 5, "max": 200},
            {"key": "ma_type", "label": "MA Type", "type": "select", "default": "sma", "values": ["sma", "ema"]},
        ],
    },
    "dual_ma": {
        "name": "Triple MA", "category": "Trend Following",
        "description": "Buy when short>mid>long MA alignment forms",
        "params": [
            {"key": "short_period", "label": "Short Period", "type": "int", "default": 5, "min": 2, "max": 20},
            {"key": "mid_period", "label": "Mid Period", "type": "int", "default": 20, "min": 10, "max": 50},
            {"key": "long_period", "label": "Long Period", "type": "int", "default": 60, "min": 30, "max": 200},
        ],
    },
    "donchian": {
        "name": "Donchian (Turtle)", "category": "Trend Following",
        "description": "Turtle trading: breakout of N-day high, exit on M-day low",
        "params": [
            {"key": "entry_period", "label": "Entry Period", "type": "int", "default": 20, "min": 10, "max": 55},
            {"key": "exit_period", "label": "Exit Period", "type": "int", "default": 10, "min": 5, "max": 30},
        ],
    },

    # ── Oscillator ──
    "rsi": {
        "name": "RSI", "category": "Oscillator",
        "description": "Buy oversold, sell overbought. Mean-reversion oscillator",
        "params": [
            {"key": "rsi_period", "label": "RSI Period", "type": "int", "default": 14, "min": 2, "max": 30},
            {"key": "oversold", "label": "Oversold", "type": "int", "default": 30, "min": 10, "max": 40},
            {"key": "overbought", "label": "Overbought", "type": "int", "default": 70, "min": 60, "max": 90},
        ],
    },
    "kdj": {
        "name": "KDJ Stochastic", "category": "Oscillator",
        "description": "Buy on KDJ golden cross in oversold zone",
        "params": [
            {"key": "kdj_period", "label": "KDJ Period", "type": "int", "default": 9, "min": 5, "max": 30},
            {"key": "oversold", "label": "Oversold", "type": "float", "default": 20, "min": 10, "max": 40},
            {"key": "overbought", "label": "Overbought", "type": "float", "default": 80, "min": 60, "max": 90},
        ],
    },
    "cci": {
        "name": "CCI", "category": "Oscillator",
        "description": "Commodity Channel Index mean reversion",
        "params": [
            {"key": "cci_period", "label": "CCI Period", "type": "int", "default": 20, "min": 10, "max": 40},
            {"key": "oversold", "label": "Oversold", "type": "float", "default": -100, "min": -200, "max": -50},
            {"key": "overbought", "label": "Overbought", "type": "float", "default": 100, "min": 50, "max": 200},
        ],
    },

    # ── Volatility ──
    "bollinger": {
        "name": "Bollinger Bands", "category": "Volatility",
        "description": "Buy at lower band, sell at upper band. Volatility mean-reversion",
        "params": [
            {"key": "bb_period", "label": "Period", "type": "int", "default": 20, "min": 5, "max": 50},
            {"key": "bb_std", "label": "Std Dev", "type": "float", "default": 2.0, "min": 1.0, "max": 3.0, "step": 0.1},
        ],
    },
    "atr_breakout": {
        "name": "ATR Breakout", "category": "Volatility",
        "description": "Buy on breakout above N×ATR channel",
        "params": [
            {"key": "atr_period", "label": "ATR Period", "type": "int", "default": 14, "min": 5, "max": 30},
            {"key": "multiplier", "label": "ATR Multiplier", "type": "float", "default": 2.0, "min": 1.0, "max": 4.0, "step": 0.5},
        ],
    },

    # ── Momentum ──
    "macd": {
        "name": "MACD", "category": "Momentum",
        "description": "MACD crosses above signal line triggers buy",
        "params": [
            {"key": "fast_period", "label": "Fast EMA", "type": "int", "default": 12, "min": 5, "max": 30},
            {"key": "slow_period", "label": "Slow EMA", "type": "int", "default": 26, "min": 10, "max": 50},
            {"key": "signal_period", "label": "Signal Period", "type": "int", "default": 9, "min": 3, "max": 20},
        ],
    },
    "momentum": {
        "name": "Momentum", "category": "Momentum",
        "description": "Buy strong momentum, exit on reversal",
        "params": [
            {"key": "lookback", "label": "Lookback Days", "type": "int", "default": 20, "min": 5, "max": 60},
            {"key": "threshold", "label": "Threshold", "type": "float", "default": 0.05, "min": 0.01, "max": 0.2, "step": 0.01},
        ],
    },

    # ── Mean Reversion ──
    "mean_reversion": {
        "name": "Mean Reversion", "category": "Mean Reversion",
        "description": "Buy when price deviates N std below mean",
        "params": [
            {"key": "period", "label": "Period", "type": "int", "default": 20, "min": 10, "max": 50},
            {"key": "entry_std", "label": "Entry Std Dev", "type": "float", "default": 2.0, "min": 1.0, "max": 3.0, "step": 0.5},
            {"key": "exit_std", "label": "Exit Std Dev", "type": "float", "default": 0.5, "min": 0.0, "max": 1.5, "step": 0.5},
        ],
    },

    # ── Volume ──
    "volume_breakout": {
        "name": "Volume Breakout", "category": "Volume",
        "description": "Buy on volume spike with rising price",
        "params": [
            {"key": "vol_period", "label": "Volume MA Period", "type": "int", "default": 20, "min": 10, "max": 50},
            {"key": "vol_multiplier", "label": "Volume Multiplier", "type": "float", "default": 1.2, "min": 1.0, "max": 4.0, "step": 0.2},
            {"key": "price_period", "label": "Price Chg Period", "type": "int", "default": 5, "min": 1, "max": 20},
        ],
    },
}

CATEGORIES = ["Trend Following", "Oscillator", "Volatility", "Momentum", "Mean Reversion", "Volume"]
