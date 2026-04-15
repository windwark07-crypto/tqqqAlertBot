"""
골든크로스/데드크로스 발생 이력을 state.json에 저장.

GitHub Actions 실행마다 환경이 초기화되므로
state.json을 레포지토리에 커밋해 상태를 유지한다.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "state.json"

_DEFAULT_STATE: dict = {
    "last_golden_cross_date": None,   # 마지막 골든크로스 날짜 (YYYY-MM-DD)
    "last_golden_cross_price": None,  # 골든크로스 당일 현재가
    "last_dead_cross_date": None,     # 마지막 데드크로스 날짜
    "last_dead_cross_price": None,    # 데드크로스 당일 현재가
    "drop_10_alerted": False,         # 10% 하락 알림 발송 여부 (가격 회복 시 초기화)
    "drop_20_alerted": False,         # 20% 하락 알림 발송 여부 (가격 회복 시 초기화)
}


def load() -> dict:
    if not STATE_FILE.exists():
        logger.info("state.json 없음, 기본값 사용")
        return _DEFAULT_STATE.copy()
    with STATE_FILE.open(encoding="utf-8") as f:
        state = json.load(f)
    logger.info("state.json 로드: %s", state)
    return state


def save(state: dict) -> None:
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    logger.info("state.json 저장 완료: %s", state)


def update_golden_cross(state: dict, date: str, price: float) -> dict:
    state["last_golden_cross_date"]  = date
    state["last_golden_cross_price"] = round(price, 2)
    return state


def update_dead_cross(state: dict, date: str, price: float) -> dict:
    state["last_dead_cross_date"]  = date
    state["last_dead_cross_price"] = round(price, 2)
    return state
