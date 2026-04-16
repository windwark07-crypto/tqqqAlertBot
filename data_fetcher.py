"""
Polygon.io API로 QQQ 종가 데이터 가져오기.

공식 API + 무료 플랜으로 시장 마감 후 15~30분 내 데이터 제공.
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

from config import LONG_MA, SYMBOL, get_polygon_api_key

logger = logging.getLogger(__name__)

BASE_URL = "https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/{from_date}/{to_date}"
PREV_URL = "https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
MIN_REQUIRED_ROWS = LONG_MA + 2  # 크로스오버 감지를 위해 최소 165행 필요


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
    현재 시각 기준으로 Polygon.io가 반환해야 할 최신 거래일을 계산.

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


def _fetch_prev_close() -> tuple[pd.Timestamp, float]:
    """Polygon.io prev 엔드포인트로 가장 최근 거래일 종가를 가져온다."""
    url = PREV_URL.format(symbol=SYMBOL)
    logger.info("Polygon.io prev API 호출 중: symbol=%s", SYMBOL)
    response = _SESSION.get(
        url,
        params={"apiKey": get_polygon_api_key()},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    if data.get("status") == "ERROR":
        raise ValueError(f"Polygon.io prev API 오류: {data.get('error')}")

    results = data.get("results")
    if not results:
        raise ValueError(f"{SYMBOL}: prev API 응답에 데이터가 없습니다.")

    r = results[0]
    return pd.Timestamp(r["t"], unit="ms").normalize(), float(r["c"])


def _fetch_close_series() -> pd.Series:
    """Polygon.io range + prev 엔드포인트를 조합해 종가 Series를 반환."""
    now_et    = datetime.now(_ET)
    from_date = (now_et - timedelta(days=730)).strftime("%Y-%m-%d")
    to_date   = (now_et + timedelta(days=1)).strftime("%Y-%m-%d")

    url = BASE_URL.format(symbol=SYMBOL, from_date=from_date, to_date=to_date)
    logger.info("Polygon.io range API 호출 중: symbol=%s", SYMBOL)

    response = _SESSION.get(
        url,
        params={"apiKey": get_polygon_api_key(), "sort": "asc", "limit": 50000},
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    if data.get("status") == "ERROR":
        raise ValueError(f"Polygon.io API 오류: {data.get('error')}")

    results = data.get("results")
    if not results:
        raise ValueError(f"{SYMBOL}: Polygon.io API 응답에 데이터가 없습니다.")

    # Unix ms → 날짜, 종가 추출
    close_series = pd.Series(
        {pd.Timestamp(r["t"], unit="ms").normalize(): r["c"] for r in results}
    ).sort_index()

    if close_series.empty:
        raise ValueError("종가 데이터가 없습니다. API 응답을 확인하세요.")

    # prev 엔드포인트로 최신 종가 보완 (range API 처리 지연 대응)
    prev_date, prev_close = _fetch_prev_close()
    if prev_date > close_series.index[-1]:
        logger.info("prev API로 최신 종가 보완: %s $%.2f", prev_date.date(), prev_close)
        close_series[prev_date] = prev_close
        close_series = close_series.sort_index()

    if len(close_series) < MIN_REQUIRED_ROWS:
        raise ValueError(
            f"데이터 부족: {len(close_series)}개 (최소 {MIN_REQUIRED_ROWS}개 필요)"
        )

    return close_series


def fetch_daily_close(max_retries: int = 4, retry_wait_sec: int = 180) -> pd.Series:
    """
    QQQ 일별 종가(Close)를 날짜 오름차순 pd.Series로 반환.

    당일 종가가 아직 확정되지 않은 경우 retry_wait_sec 간격으로
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
