"""
Yahoo Finance API 직접 호출로 QQQ 종가 데이터 가져오기.

비공식 API이나 API 키 불필요.
range=2y로 2년치 일봉 데이터 수신 → 163일 MA 계산에 충분.
"""
import logging
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import LONG_MA, SYMBOL

logger = logging.getLogger(__name__)

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
MIN_REQUIRED_ROWS = LONG_MA + 2  # 크로스오버 감지를 위해 최소 165행 필요

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


def _build_session() -> requests.Session:
    """지수 백오프 재시도 세션 생성."""
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1,  # 1s, 2s, 4s 간격
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    return session


_SESSION = _build_session()
_ET = ZoneInfo("America/New_York")


def _expected_latest_trading_date() -> date:
    """
    현재 시각 기준으로 Yahoo Finance가 반환해야 할 최신 거래일을 계산.

    미국 주식 시장은 ET 16:30 이후 당일 종가가 확정되므로
    ET 16:30 이전이면 전 거래일, 이후면 당일을 기대값으로 반환.
    (미국 공휴일은 미고려)
    """
    now_et = datetime.now(_ET)
    market_close_et = now_et.replace(hour=16, minute=30, second=0, microsecond=0)
    expected = now_et.date() if now_et >= market_close_et else now_et.date() - timedelta(days=1)
    # 주말이면 직전 금요일로
    while expected.weekday() >= 5:  # 5=토, 6=일
        expected -= timedelta(days=1)
    return expected


def _fetch_chart_result(symbol: str, params: dict) -> dict:
    """Yahoo Finance Chart API를 호출하고 result[0]를 반환."""
    url = BASE_URL.format(symbol=symbol)
    logger.info("Yahoo Finance API 호출 중: symbol=%s", symbol)
    response = _SESSION.get(url, headers=HEADERS, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    chart = data.get("chart", {})

    if chart.get("error"):
        raise ValueError(f"Yahoo Finance API 오류: {chart['error']}")

    result = chart.get("result")
    if not result:
        raise ValueError(f"{symbol}: Yahoo Finance API 응답에 데이터가 없습니다.")

    return result[0]


def fetch_latest_close(symbol: str) -> float:
    """
    특정 심볼의 최근 종가 1개를 반환.

    Returns:
        float: 최근 종가

    Raises:
        ValueError: 응답 오류 또는 데이터 없음
        requests.HTTPError: HTTP 오류
    """
    result = _fetch_chart_result(symbol, {"interval": "1d", "range": "5d"})
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
    closes = [c for c in closes if c is not None]

    if not closes:
        raise ValueError(f"{symbol} 종가 데이터가 없습니다.")

    return float(closes[-1])


def _fetch_close_series() -> pd.Series:
    """Yahoo Finance에서 종가 Series를 한 번 가져와 반환."""
    result = _fetch_chart_result(SYMBOL, {"interval": "1d", "range": "2y"})

    timestamps = result.get("timestamp", [])
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])

    if not timestamps or not closes:
        raise ValueError("타임스탬프 또는 종가 데이터가 없습니다.")

    close_series = pd.Series(
        {
            pd.Timestamp(ts, unit="s").normalize(): close
            for ts, close in zip(timestamps, closes)
            if close is not None
        }
    ).sort_index()

    if close_series.empty:
        raise ValueError("종가 데이터가 모두 None입니다. API 응답을 확인하세요.")

    if len(close_series) < MIN_REQUIRED_ROWS:
        raise ValueError(
            f"데이터 부족: {len(close_series)}개 (최소 {MIN_REQUIRED_ROWS}개 필요)"
        )

    return close_series


def fetch_daily_close(max_retries: int = 3, retry_wait_sec: int = 600) -> pd.Series:
    """
    QQQ 일별 종가(Close)를 날짜 오름차순 pd.Series로 반환.

    Yahoo Finance가 당일 종가를 아직 확정하지 않은 경우 retry_wait_sec 간격으로
    최대 max_retries회 재시도한다.

    Returns:
        pd.Series: 인덱스=날짜(Timestamp), 값=종가(float), 날짜 오름차순

    Raises:
        ValueError: 응답 오류 또는 데이터 부족
        requests.HTTPError: HTTP 오류
    """
    expected = _expected_latest_trading_date()

    for attempt in range(1, max_retries + 1):
        close_series = _fetch_close_series()
        latest = close_series.index[-1].date()

        logger.info(
            "수신된 데이터: %d개 거래일 (최신: %s, 예상: %s)",
            len(close_series), latest, expected,
        )

        if latest >= expected:
            return close_series

        if attempt < max_retries:
            logger.warning(
                "최신 데이터(%s)가 예상 거래일(%s)보다 오래됨 — %d초 후 재시도 (%d/%d)",
                latest, expected, retry_wait_sec, attempt, max_retries - 1,
            )
            time.sleep(retry_wait_sec)
        else:
            logger.warning(
                "재시도 %d회 후에도 최신 데이터 없음 (최신: %s, 예상: %s) — 현재 데이터로 진행",
                max_retries, latest, expected,
            )

    return close_series
