"""
QQQ 이동평균선 알림 메인 실행 파이프라인.

실행 순서:
  1. 종가 데이터 수집 (Alpha Vantage)
  2. MA 계산 및 신호 감지
  3. 텔레그램 알림 발송
"""
import logging
import sys

from data_fetcher import fetch_daily_close
from ma_calculator import calculate_signals
from notifier import notify

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def run() -> None:
    logger.info("===== QQQ MA 알림 작업 시작 =====")

    try:
        logger.info("[1/3] Alpha Vantage에서 QQQ 종가 데이터 수집")
        close_series = fetch_daily_close()

        logger.info("[2/3] 이동평균 계산 및 신호 감지")
        ma_result = calculate_signals(close_series)

        logger.info("[3/3] 텔레그램 알림 발송 (신호: %s)", ma_result.signal)
        notify(ma_result)

        logger.info("===== 작업 완료 =====")

    except KeyError as e:
        logger.error("환경변수 누락: %s", e)
        logger.error("GitHub Secrets 또는 .env 파일을 확인하세요.")
        sys.exit(1)
    except ValueError as e:
        logger.error("데이터/API 오류: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("예기치 않은 오류 발생: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    run()
