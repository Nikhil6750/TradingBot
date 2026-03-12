"""
models.py — SQLAlchemy ORM models for AlgoTradeX.

Tables:
  User, Strategy, BacktestSession, Trade, PerformanceMetrics, OptimizationResult
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime,
    ForeignKey, Boolean, Enum as SAEnum,
)
from sqlalchemy.orm import relationship

from backend.database.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id               = Column(Integer, primary_key=True, index=True)
    email            = Column(String(255), unique=True, index=True, nullable=False)
    phone            = Column(String(20),  nullable=True)
    google_id        = Column(String(255), nullable=True, unique=True)
    auth_provider    = Column(String(50),  default="email")
    password_hash    = Column(String(255), nullable=False)
    experience_level = Column(String(50),  default="intermediate")   # beginner / intermediate / advanced
    preferred_market = Column(String(50),  default="forex")          # forex / crypto / equities
    created_at       = Column(DateTime,    default=_now, nullable=False)

    strategies       = relationship("Strategy",       back_populates="user", cascade="all, delete-orphan")
    backtest_sessions = relationship("BacktestSession", back_populates="user", cascade="all, delete-orphan")


# ── Strategies ────────────────────────────────────────────────────────────────
class Strategy(Base):
    __tablename__ = "strategies"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    strategy_name = Column(String(255), nullable=False)
    strategy_type = Column(String(50),  nullable=False)   # template / parameter / rules / code / ai
    strategy_json = Column(Text,        nullable=False, default="{}")
    created_at    = Column(DateTime,    default=_now, nullable=False)

    user     = relationship("User",           back_populates="strategies")
    sessions = relationship("BacktestSession", back_populates="strategy", cascade="all, delete-orphan")

    @property
    def config(self) -> dict:
        return json.loads(self.strategy_json)

    @config.setter
    def config(self, value: dict) -> None:
        self.strategy_json = json.dumps(value)


# ── BacktestSessions ──────────────────────────────────────────────────────────
class BacktestSession(Base):
    __tablename__ = "backtest_sessions"

    id              = Column(Integer, primary_key=True, index=True)
    user_id         = Column(Integer, ForeignKey("users.id"),    nullable=True)
    strategy_id     = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    symbol          = Column(String(20),  nullable=False, default="UNKNOWN")
    timeframe       = Column(String(10),  nullable=True)
    start_date      = Column(DateTime,    nullable=True)
    end_date        = Column(DateTime,    nullable=True)
    initial_capital = Column(Float,       nullable=False, default=10_000.0)
    created_at      = Column(DateTime,    default=_now, nullable=False)

    user     = relationship("User",     back_populates="backtest_sessions")
    strategy = relationship("Strategy", back_populates="sessions")
    trades   = relationship("Trade",             back_populates="session", cascade="all, delete-orphan")
    metrics  = relationship("PerformanceMetrics", back_populates="session",
                            uselist=False, cascade="all, delete-orphan")
    optimizations = relationship("OptimizationResult", back_populates="session",
                                 cascade="all, delete-orphan")


# ── Trades ────────────────────────────────────────────────────────────────────
class Trade(Base):
    __tablename__ = "trades"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("backtest_sessions.id"), nullable=False)
    entry_time  = Column(Float,  nullable=True)   # unix timestamp
    exit_time   = Column(Float,  nullable=True)
    entry_price = Column(Float,  nullable=True)
    exit_price  = Column(Float,  nullable=True)
    position    = Column(String(10), nullable=False, default="BUY")  # BUY / SELL
    pnl         = Column(Float,  nullable=False, default=0.0)
    duration    = Column(Float,  nullable=True)   # seconds

    session = relationship("BacktestSession", back_populates="trades")


# ── PerformanceMetrics ────────────────────────────────────────────────────────
class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"

    id            = Column(Integer, primary_key=True, index=True)
    session_id    = Column(Integer, ForeignKey("backtest_sessions.id"), nullable=False)
    win_rate      = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    sharpe_ratio  = Column(Float, nullable=True)
    max_drawdown  = Column(Float, nullable=True)
    total_return  = Column(Float, nullable=True)
    total_trades  = Column(Integer, nullable=True)
    best_trade    = Column(Float, nullable=True)
    worst_trade   = Column(Float, nullable=True)
    expectancy    = Column(Float, nullable=True)
    avg_trade     = Column(Float, nullable=True)

    session = relationship("BacktestSession", back_populates="metrics")


# ── OptimizationResults ───────────────────────────────────────────────────────
class OptimizationResult(Base):
    __tablename__ = "optimization_results"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(Integer, ForeignKey("backtest_sessions.id"), nullable=True)
    parameters   = Column(Text,  nullable=False, default="{}")   # JSON dict
    sharpe_ratio = Column(Float, nullable=True)
    profit       = Column(Float, nullable=True)
    win_rate     = Column(Float, nullable=True)
    created_at   = Column(DateTime, default=_now, nullable=False)

    session = relationship("BacktestSession", back_populates="optimizations")

    @property
    def params(self) -> dict:
        return json.loads(self.parameters)

    @params.setter
    def params(self, value: dict) -> None:
        self.parameters = json.dumps(value)


# ── FXReplay Style Session System ─────────────────────────────────────────────
class TradingSession(Base):
    __tablename__ = "sessions"
    
    id           = Column(Integer, primary_key=True, index=True)
    session_name = Column(String(255), nullable=False)
    broker       = Column(String(50),  nullable=False, default="oanda")   # oanda / dukascopy / fxcm / binance
    symbol       = Column(String(50),  nullable=False)
    balance      = Column(Float, nullable=False, default=10000.0)
    start_date   = Column(DateTime, nullable=True)
    end_date     = Column(DateTime, nullable=True)
    created_at   = Column(DateTime, default=_now, nullable=False)

    session_trades = relationship("SessionTrade", back_populates="session", cascade="all, delete-orphan")

class SessionTrade(Base):
    # Named session_trades instead of trades to prevent dropping existing Trade table
    __tablename__ = "session_trades" 
    
    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    symbol      = Column(String(50), nullable=False)
    side        = Column(String(10), nullable=False)  # BUY or SELL
    entry_price = Column(Float, nullable=False)
    exit_price  = Column(Float, nullable=True)
    quantity    = Column(Float, nullable=False)
    pnl         = Column(Float, nullable=True)
    timestamp   = Column(Float, nullable=True) # or DateTime unix float

    session = relationship("TradingSession", back_populates="session_trades")

