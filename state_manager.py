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


def _default_state() -> dict:
    """항상 새로운 기본 상태 딕셔너리를 반환하는 팩토리 함수."""
    return {
        "last_golden_cross_date": None,        # 마지막 골든크로스 날짜 (YYYY-MM-DD)
        "last_golden_cross_price": None,       # 골든크로스 당일 QQQ 현재가
        "last_golden_cross_tqqq_price": None,  # 골든크로스 당일 TQQQ 종가
        "last_dead_cross_date": None,          # 마지막 데드크로스 날짜
        "last_dead_cross_price": None,         # 데드크로스 당일 현재가
        "drop_10_alerted": False,              # 10% 하락 알림 발송 여부 (가격 회복 시 초기화)
        "drop_20_alerted": False,              # 20% 하락 알림 발송 여부 (가격 회복 시 초기화)
        "tqqq_25_alerted": False,              # TQQQ 매수가 대비 25% 상승 알림 발송 여부
    }


def load() -> dict:
    if not STATE_FILE.exists():
        logger.info("state.json 없음, 기본값 사용")
        return _default_state()
    with STATE_FILE.open(encoding="utf-8") as f:
        state = json.load(f)
    logger.info("state.json 로드: %s", state)
    return state


def save(state: dict) -> None:
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    logger.info("state.json 저장 완료: %s", state)


def set_drop_10_alerted(state: dict) -> None:
    state["drop_10_alerted"] = True


def set_drop_20_alerted(state: dict) -> None:
    state["drop_20_alerted"] = True
    state["drop_10_alerted"] = True  # 20% 달성 시 10% 플래그도 함께 처리


def reset_drop_flags(state: dict) -> None:
    state["drop_10_alerted"] = False
    state["drop_20_alerted"] = False


def set_tqqq_25_alerted(state: dict) -> None:
    state["tqqq_25_alerted"] = True


def update_golden_cross(state: dict, date: str, price: float, tqqq_price: float) -> dict:
    state["last_golden_cross_date"]        = date
    state["last_golden_cross_price"]       = round(price, 2)
    state["last_golden_cross_tqqq_price"]  = round(tqqq_price, 2)
    state["last_dead_cross_date"]          = None
    state["last_dead_cross_price"]         = None
    state["drop_10_alerted"]               = False
    state["drop_20_alerted"]               = False
    state["tqqq_25_alerted"]               = False
    return state


def update_dead_cross(state: dict, date: str, price: float) -> dict:
    state["last_dead_cross_date"]         = date
    state["last_dead_cross_price"]        = round(price, 2)
    state["last_golden_cross_date"]       = None
    state["last_golden_cross_price"]      = None
    state["last_golden_cross_tqqq_price"] = None
    state["tqqq_25_alerted"]              = False
    return state
