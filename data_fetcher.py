"""
Yahoo Finance API 직접 호출로 QQQ 종가 데이터 가져오기.

비공식 API이나 API 키 불필요.
range=2y로 2년치 일봉 데이터 수신 → 163일 MA 계산에 충분.
"""
import logging

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


def fetch_daily_close() -> pd.Series:
    """
    QQQ 일별 종가(Close)를 날짜 오름차순 pd.Series로 반환.

    Returns:
        pd.Series: 인덱스=날짜(Timestamp, UTC→날짜), 값=종가(float), 날짜 오름차순

    Raises:
        ValueError: 응답 오류 또는 데이터 부족
        requests.HTTPError: HTTP 오류
    """
    result = _fetch_chart_result(SYMBOL, {"interval": "1d", "range": "2y"})

    timestamps = result.get("timestamp", [])
    closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])

    if not timestamps or not closes:
        raise ValueError("타임스탬프 또는 종가 데이터가 없습니다.")

    # timestamp(Unix) → 날짜, None 제거
    close_series = pd.Series(
        {
            pd.Timestamp(ts, unit="s").normalize(): close
            for ts, close in zip(timestamps, closes)
            if close is not None
        }
    ).sort_index()

    if close_series.empty:
        raise ValueError("종가 데이터가 모두 None입니다. API 응답을 확인하세요.")

    logger.info("수신된 데이터: %d개 거래일 (최근: %s)", len(close_series), close_series.index[-1].date())

    if len(close_series) < MIN_REQUIRED_ROWS:
        raise ValueError(
            f"데이터 부족: {len(close_series)}개 (최소 {MIN_REQUIRED_ROWS}개 필요)"
        )

    return close_series
