"""
이동평균선 계산 및 크로스오버 신호 감지.

크로스오버 감지 방식: 어제/오늘 2일치 MA 방향 비교
  - 골든크로스: 어제 short_ma <= long_ma  AND  오늘 short_ma > long_ma
  - 데드크로스: 어제 short_ma >= long_ma  AND  오늘 short_ma < long_ma
  - 위(지속):   크로스 없이 오늘 short_ma > long_ma
  - 아래(지속): 크로스 없이 오늘 short_ma <= long_ma

52주 고가 대비 하락 감지:
  - 최근 252 거래일 종가 최고값 기준
  - 현재가가 52주 고가 대비 10% 이상 하락 시 매수 알림
"""
import logging
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from config import LONG_MA, SHORT_MA

logger = logging.getLogger(__name__)

# 미국 주식 연간 거래일 수 (52주 × 5일 - 공휴일 약 10일 ≈ 252일)
TRADING_DAYS_1Y    = 252
DROP_THRESHOLD_10  = 0.10  # 10% 하락 기준
DROP_THRESHOLD_20  = 0.20  # 20% 하락 기준

SignalType = Literal["golden_cross", "dead_cross", "above", "below"]


@dataclass
class MAResult:
    signal: SignalType
    short_ma_value: float
    long_ma_value: float
    today_date: str
    short_period: int
    long_period: int
    current_price: float
    high_52w: float
    drop_pct: float          # 52주 고가 대비 하락률 (0.10 = 10%)
    is_52w_drop_10_alert: bool  # 10% 이상 하락 시 True
    is_52w_drop_20_alert: bool  # 20% 이상 하락 시 True


def calculate_signals(close_series: pd.Series) -> MAResult:
    """
    종가 Series에서 이동평균 및 52주 고가 대비 하락률을 계산.

    Args:
        close_series: 날짜 오름차순 종가 pd.Series

    Returns:
        MAResult: 신호 타입, MA 수치, 52주 고가 분석 포함

    Raises:
        ValueError: 데이터 부족으로 MA 계산 불가
    """
    short_ma = close_series.rolling(window=SHORT_MA, min_periods=SHORT_MA).mean()
    long_ma  = close_series.rolling(window=LONG_MA,  min_periods=LONG_MA).mean()

    recent_short = short_ma.iloc[-2:]
    recent_long  = long_ma.iloc[-2:]

    if recent_short.isna().any() or recent_long.isna().any():
        raise ValueError(
            f"MA 계산 불가: NaN 포함. 최소 {LONG_MA + 1}일치 데이터 필요"
        )

    short_yesterday = float(recent_short.iloc[0])
    short_today     = float(recent_short.iloc[1])
    long_yesterday  = float(recent_long.iloc[0])
    long_today      = float(recent_long.iloc[1])

    today_date    = close_series.index[-1].strftime("%Y-%m-%d")
    current_price = float(close_series.iloc[-1])

    # 52주 고가: 최근 252 거래일 종가 최고값
    lookback      = min(TRADING_DAYS_1Y, len(close_series))
    high_52w      = float(close_series.iloc[-lookback:].max())
    drop_pct      = (high_52w - current_price) / high_52w

    logger.info(
        "[%s] %d일MA=%.4f | %d일MA=%.4f | 현재가=%.2f | 52주고가=%.2f | 고가대비하락=%.2f%%",
        today_date,
        SHORT_MA, short_today,
        LONG_MA,  long_today,
        current_price,
        high_52w,
        drop_pct * 100,
    )

    if short_yesterday <= long_yesterday and short_today > long_today:
        signal: SignalType = "golden_cross"
    elif short_yesterday >= long_yesterday and short_today < long_today:
        signal = "dead_cross"
    elif short_today > long_today:
        signal = "above"
    else:
        signal = "below"

    logger.info(
        "MA 신호: %s | 52주고가 10%% 하락: %s | 20%% 하락: %s",
        signal,
        drop_pct >= DROP_THRESHOLD_10,
        drop_pct >= DROP_THRESHOLD_20,
    )

    return MAResult(
        signal=signal,
        short_ma_value=short_today,
        long_ma_value=long_today,
        today_date=today_date,
        short_period=SHORT_MA,
        long_period=LONG_MA,
        current_price=current_price,
        high_52w=high_52w,
        drop_pct=drop_pct,
        is_52w_drop_10_alert=drop_pct >= DROP_THRESHOLD_10,
        is_52w_drop_20_alert=drop_pct >= DROP_THRESHOLD_20,
    )
