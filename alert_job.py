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
from notifier import dispatch_notification, NotificationKind
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
        logger.info("[1/4] Polygon.io에서 QQQ 종가 데이터 수집")
        close_series = fetch_daily_close()

        logger.info("[2/4] 이동평균 계산 및 신호 감지")
        ma_result = calculate_signals(close_series)

        logger.info("[3/4] 상태 파일 로드")
        state = state_manager.load()

        logger.info("[4/4] 텔레그램 알림 발송 (신호: %s)", ma_result.signal)

        kind = dispatch_notification(ma_result, state)

        # 알림 종류에 따른 state 플래그 갱신
        if kind == NotificationKind.DROP_20:
            state_manager.set_drop_20_alerted(state)
        elif kind == NotificationKind.DROP_10:
            state_manager.set_drop_10_alerted(state)
        elif kind == NotificationKind.QQQ_RISE:
            state_manager.set_qqq_8pct_alerted(state)

        # 가격 회복 시 drop 플래그 초기화 (dead_cross 시에는 초기화 제외)
        if kind != NotificationKind.DEAD_CROSS:
            if not ma_result.is_52w_drop_10_alert:
                state_manager.reset_drop_flags(state)
            elif not ma_result.is_52w_drop_20_alert:
                state_manager.reset_drop_20_flag(state)

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
        logger.error("예기치 않은 키 오류: %s — 환경변수 또는 state.json 키를 확인하세요.", e)
        sys.exit(1)
    except ValueError as e:
        logger.error("데이터/API 오류: %s", e)
        sys.exit(1)
    except Exception as e:
        logger.exception("예기치 않은 오류 발생: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    run()
