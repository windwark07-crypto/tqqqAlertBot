"""
환경변수 설정 로더.

GitHub Actions: Secrets → env 블록 → os.environ
로컬 개발:      .env 파일 → python-dotenv → os.environ
"""
import os

# 로컬 .env가 있으면 로드, 없으면(GitHub Actions 등) 조용히 무시
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# 필수 환경변수 (누락 시 KeyError 즉시 발생)
TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID: str   = os.environ["TELEGRAM_CHAT_ID"]

# 설정값
SYMBOL: str   = "QQQ"
SHORT_MA: int = 3    # 단기 이동평균 기간 (일)
LONG_MA: int  = 163  # 장기 이동평균 기간 (일)
