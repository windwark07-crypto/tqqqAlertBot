"""
환경변수 설정 로더.

GitHub Actions: Secrets → env 블록 → os.environ
로컬 개발:      .env 파일 → python-dotenv → os.environ
"""
import os
from functools import lru_cache

# 로컬 .env가 있으면 로드, 없으면(GitHub Actions 등) 조용히 무시
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _require_env(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise KeyError(
            f"필수 환경변수 '{key}'가 설정되지 않았습니다. "
            "GitHub Secrets 또는 .env 파일을 확인하세요."
        )
    return value


# 필수 환경변수 — 실제 사용 시점에 평가 (임포트 시 즉시 평가하지 않음)
@lru_cache(maxsize=None)
def get_telegram_token() -> str:
    return _require_env("TELEGRAM_BOT_TOKEN")

@lru_cache(maxsize=None)
def get_telegram_chat_id() -> str:
    return _require_env("TELEGRAM_CHAT_ID")

@lru_cache(maxsize=None)
def get_polygon_api_key() -> str:
    return _require_env("POLYGON_API_KEY")

# 설정값 (환경변수로 오버라이드 가능)
def _get_int_env(key: str, default: int) -> int:
    raw = os.getenv(key, str(default))
    try:
        return int(raw)
    except ValueError:
        raise ValueError(
            f"환경변수 '{key}'는 정수여야 합니다. 현재 값: '{raw}'"
        )

SYMBOL: str   = os.getenv("SYMBOL", "QQQ")
SHORT_MA: int = _get_int_env("SHORT_MA", 3)    # 단기 이동평균 기간 (일)
LONG_MA: int  = _get_int_env("LONG_MA", 163)   # 장기 이동평균 기간 (일)
