"""
QQQ 이동평균선 알림 메인 실행 파이프라인.

실행 순서:
  1. 종가 데이터 수집
  2. MA 계산 및 신호 감지
  3. 상태 로드 (state.json)
  4. 텔레그램 알림 발송
  5. 골든크로스/데드크로스 발생 시 상태 저장
"""
import logging
import sys

from data_fetcher import fetch_daily_close
from ma_calculator import calculate_signals
from notifier import notify_ma, notify_drop
import state_manager

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
        logger.info("[1/4] Yahoo Finance에서 QQQ 종가 데이터 수집")
        close_series = fetch_daily_close()

        logger.info("[2/4] 이동평균 계산 및 신호 감지")
        ma_result = calculate_signals(close_series)

        logger.info("[3/4] 상태 파일 로드")
        state = state_manager.load()

        logger.info("[4/4] 텔레그램 알림 발송 (신호: %s)", ma_result.signal)

        # 이벤트별 메시지 1개만 발송 (데드크로스는 항상 데드크로스 메시지만)
        if ma_result.signal == "dead_cross":
            notify_ma(ma_result, state)
        elif ma_result.is_52w_drop_20_alert and not state.get("drop_20_alerted"):
            notify_drop(ma_result, 20)
            state["drop_20_alerted"] = True
            state["drop_10_alerted"] = True
        elif ma_result.is_52w_drop_10_alert and not state.get("drop_10_alerted"):
            notify_drop(ma_result, 10)
            state["drop_10_alerted"] = True
        else:
            notify_ma(ma_result, state)

        # 가격 회복 시 플래그 초기화
        if not ma_result.is_52w_drop_10_alert:
            state["drop_10_alerted"] = False
            state["drop_20_alerted"] = False
        elif not ma_result.is_52w_drop_20_alert:
            state["drop_20_alerted"] = False

        # 크로스 발생 시 state 업데이트
        if ma_result.signal == "golden_cross":
            state = state_manager.update_golden_cross(
                state, ma_result.today_date, ma_result.current_price
            )
        elif ma_result.signal == "dead_cross":
            state = state_manager.update_dead_cross(
                state, ma_result.today_date, ma_result.current_price
            )

        state_manager.save(state)

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
