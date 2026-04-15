"""
텔레그램 Bot API를 통한 알림 메시지 발송.
4가지 신호별 메시지 템플릿 포함.
"""
import logging

import requests

import state_manager
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from ma_calculator import MAResult, SignalType

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
QQQ_RISE_THRESHOLD = 0.08  # 골든크로스 매수가 대비 QQQ 8% 상승 시 일부 매도 알림

_TEMPLATES: dict[SignalType, str] = {
    "golden_cross": (
        "🟢 <b>[나스닥100 골든크로스 발생]</b>\n"
        "\n"
        "📈 {short_period}일 이동평균선이 {long_period}일 이동평균선을 <b>위로 돌파</b>했습니다!\n"
        "\n"
        "• 기준일: {date}\n"
        "• 기준가: <b>{current_price:.2f}</b>\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "💡 KODEX 미국나스닥100 레버리지(합성 H)(409820) 전액 매수!!\n"
    ),
    "dead_cross": (
        "🔴 <b>[나스닥100 데드크로스 발생]</b>\n"
        "\n"
        "📉 {short_period}일 이동평균선이 {long_period}일 이동평균선을 <b>아래로 돌파</b>했습니다!\n"
        "\n"
        "• 기준일: {date}\n"
        "• 기준가: <b>{current_price:.2f}</b>\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "⚠️ KODEX 미국나스닥100 레버리지(합성 H)(409820) 전액 매도!!"
    ),
    "above": (
        "🔵 <b>[나스닥100 MA 현황]</b>\n"
        "\n"
        "📊 {short_period}일 이동평균선이 {long_period}일 이동평균선 <b>위에서 유지</b> 중입니다.\n"
        "\n"
        "• 기준일: {date}\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "✅ 상승 추세 유지 홀딩 추천"
    ),
    "below": (
        "⚫ <b>[나스닥100 MA 현황]</b>\n"
        "\n"
        "📊 {short_period}일 이동평균선이 {long_period}일 이동평균선 <b>아래에서 유지</b> 중입니다.\n"
        "\n"
        "• 기준일: {date}\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "⚠️ 하락 추세 유지 관망 추천"
    ),
}


_DROP_TEMPLATES: dict[int, str] = {
    10: (
        "🚨 <b>[나스닥100 52주 최고가 대비 10% 하락]</b>\n"
        "\n"
        "📉 금일 종가 52주 최고가 대비 <b>{drop_pct:.1f}% 하락</b>했습니다.\n"
        "\n"
        "• 기준일: {date}\n"
        "• 현재가: <b>{current_price:.2f}</b>\n"
        "• 52주 최고가: <b>{high_52w:.2f}</b>\n"
        "\n"
        "💡 KODEX 미국나스닥100 레버리지(합성 H)(409820) 총 보유금의 30% 매수!!"
    ),
    20: (
        "🚨 <b>[나스닥100 52주 최고가 대비 20% 하락]</b>\n"
        "\n"
        "📉 금일 종가가 52주 최고가 대비 <b>{drop_pct:.1f}% 하락</b>했습니다.\n"
        "\n"
        "• 기준일: {date}\n"
        "• 현재가: <b>{current_price:.2f}</b>\n"
        "• 52주 최고가: <b>{high_52w:.2f}</b>\n"
        "\n"
        "💡 KODEX 미국나스닥100 레버리지(합성 H)(409820) 보유금의 30% 추가 매수!!(총 60%)"
    ),
}


_QQQ_8PCT_TEMPLATE = (
    "💰 <b>[나스닥100 8% 상승]</b>\n"
    "\n"
    "📈 나스닥100 종가가 매수가 대비 <b>{rise_pct:.1f}% 상승</b>했습니다!\n"
    "\n"
    "• 기준일: {date}\n"
    "• 현재가: <b>{qqq_price:.2f}</b>\n"
    "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
    "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
    "\n"
    "💡 KODEX 미국나스닥100 레버리지(합성 H)(409820) 보유량의 30% 매도!!"
)


def build_message(result: MAResult) -> str:
    template = _TEMPLATES[result.signal]
    message = template.format(
        short_period=result.short_period,
        long_period=result.long_period,
        short_ma=result.short_ma_value,
        long_ma=result.long_ma_value,
        current_price=result.current_price,
        date=result.today_date,
    )

    return message


def _build_drop_message(template: str, result: MAResult) -> str:
    return template.format(
        drop_pct=result.drop_pct * 100,
        current_price=result.current_price,
        high_52w=result.high_52w,
        date=result.today_date,
    )


def send_telegram_message(text: str) -> None:
    """
    텔레그램 Bot API로 메시지 발송.

    Raises:
        requests.HTTPError: HTTP 오류 응답
        ValueError: 텔레그램 API가 ok=false 반환
    """
    url = TELEGRAM_API_URL.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    logger.info("텔레그램 메시지 발송 중 (chat_id=%s)", TELEGRAM_CHAT_ID)
    response = requests.post(url, json=payload, timeout=15)
    response.raise_for_status()

    result = response.json()
    if not result.get("ok"):
        raise ValueError(f"텔레그램 API 오류: {result}")

    logger.info("텔레그램 메시지 발송 완료")


def notify_ma(ma_result: MAResult) -> None:
    """MA 신호 메시지 발송."""
    send_telegram_message(build_message(ma_result))


def notify_drop(ma_result: MAResult, level: int) -> None:
    """52주 신고가 대비 하락 알림 발송. level: 10 또는 20"""
    logger.info("52주 고가 대비 %.2f%% 하락 — %d%% 하락 알림 발송", ma_result.drop_pct * 100, level)
    send_telegram_message(_build_drop_message(_DROP_TEMPLATES[level], ma_result))


def notify_partial_sell(ma_result: MAResult, rise_pct: float) -> None:
    """QQQ 8% 상승 시 일부 매도 알림 발송."""
    text = _QQQ_8PCT_TEMPLATE.format(
        rise_pct=rise_pct * 100,
        date=ma_result.today_date,
        qqq_price=ma_result.current_price,
        short_period=ma_result.short_period,
        long_period=ma_result.long_period,
        short_ma=ma_result.short_ma_value,
        long_ma=ma_result.long_ma_value,
    )
    logger.info("QQQ %.2f%% 상승 — 일부 매도 알림 발송", rise_pct * 100)
    send_telegram_message(text)


def dispatch_notification(ma_result: MAResult, state: dict) -> None:
    """
    신호 우선순위에 따라 적절한 알림을 발송하고 state 플래그를 갱신.

    우선순위: dead_cross > 20% 하락 > 10% 하락 > QQQ 8% 상승 > MA 현황

    Args:
        ma_result:  MA 계산 결과
        state:      현재 상태 딕셔너리 (플래그가 인플레이스로 갱신됨)
    """
    if ma_result.signal == "dead_cross":
        notify_ma(ma_result)
        return

    if ma_result.is_52w_drop_20_alert and not state.get("drop_20_alerted"):
        notify_drop(ma_result, 20)
        state_manager.set_drop_20_alerted(state)
        return

    if ma_result.is_52w_drop_10_alert and not state.get("drop_10_alerted"):
        notify_drop(ma_result, 10)
        state_manager.set_drop_10_alerted(state)
        return

    if (
        ma_result.signal == "above"
        and not state.get("qqq_8pct_alerted")
        and state.get("last_golden_cross_price")
    ):
        buy_price = state["last_golden_cross_price"]
        rise_pct  = (ma_result.current_price - buy_price) / buy_price
        if rise_pct >= QQQ_RISE_THRESHOLD:
            notify_partial_sell(ma_result, rise_pct)
            state_manager.set_qqq_8pct_alerted(state)
            return

    notify_ma(ma_result)
