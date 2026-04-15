"""
이동평균선 계산 및 크로스오버 신호 감지.

크로스오버 감지 방식: 어제/오늘 2일치 MA 방향 비교
  - 골든크로스: 어제 short_ma <= long_ma  AND  오늘 short_ma > long_ma
  - 데드크로스: 어제 short_ma >= long_ma  AND  오늘 short_ma < long_ma
  - 위(지속):   크로스 없이 오늘 short_ma > long_ma
  - 아래(지속): 크로스 없이 오늘 short_ma <= long_ma
"""
import logging
from dataclasses import dataclass
from typing import Literal

import pandas as pd

from config import LONG_MA, SHORT_MA

logger = logging.getLogger(__name__)

SignalType = Literal["golden_cross", "dead_cross", "above", "below"]


@dataclass
class MAResult:
    signal: SignalType
    short_ma_value: float
    long_ma_value: float
    today_date: str
    short_period: int
    long_period: int


def calculate_signals(close_series: pd.Series) -> MAResult:
    """
    종가 Series에서 이동평균을 계산하고 신호를 감지.

    Args:
        close_series: 날짜 오름차순 종가 pd.Series

    Returns:
        MAResult: 신호 타입 및 MA 수치 포함

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

    today_date = close_series.index[-1].strftime("%Y-%m-%d")

    logger.info(
        "[%s] %d일MA=%.4f | %d일MA=%.4f | 전일 %d일MA=%.4f | 전일 %d일MA=%.4f",
        today_date,
        SHORT_MA, short_today,
        LONG_MA,  long_today,
        SHORT_MA, short_yesterday,
        LONG_MA,  long_yesterday,
    )

    if short_yesterday <= long_yesterday and short_today > long_today:
        signal: SignalType = "golden_cross"
    elif short_yesterday >= long_yesterday and short_today < long_today:
        signal = "dead_cross"
    elif short_today > long_today:
        signal = "above"
    else:
        signal = "below"

    logger.info("감지된 신호: %s", signal)

    return MAResult(
        signal=signal,
        short_ma_value=short_today,
        long_ma_value=long_today,
        today_date=today_date,
        short_period=SHORT_MA,
        long_period=LONG_MA,
    )
