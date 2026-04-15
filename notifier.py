"""
텔레그램 Bot API를 통한 알림 메시지 발송.
4가지 신호별 메시지 템플릿 포함.
"""
import logging

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from ma_calculator import MAResult, SignalType

logger = logging.getLogger(__name__)

TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendMessage"

_TEMPLATES: dict[SignalType, str] = {
    "golden_cross": (
        "🟢 <b>[골든크로스 발생]</b> QQQ\n"
        "\n"
        "📈 {short_period}일 MA가 {long_period}일 MA를 <b>위로 돌파</b>했습니다!\n"
        "\n"
        "• 기준일: {date}\n"
        "• 기준가: <b>{current_price:.2f}</b>\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "💡 TQQQ 전액 매수!!\n"
        "🗓 매수일로 기록됩니다."
    ),
    "dead_cross": (
        "🔴 <b>[데드크로스 발생]</b> QQQ\n"
        "\n"
        "📉 {short_period}일 MA가 {long_period}일 MA를 <b>아래로 돌파</b>했습니다!\n"
        "\n"
        "• 기준일: {date}\n"
        "• 기준가: <b>{current_price:.2f}</b>\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "⚠️ TQQQ 전액 매도!!"
    ),
    "above": (
        "🔵 <b>[MA 현황]</b> QQQ\n"
        "\n"
        "📊 {short_period}일 MA가 {long_period}일 MA <b>위</b>에 있습니다.\n"
        "\n"
        "• 기준일: {date}\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "✅ 상승 추세 유지 홀딩 추천"
    ),
    "below": (
        "⚫ <b>[MA 현황]</b> QQQ\n"
        "\n"
        "📊 {short_period}일 MA가 {long_period}일 MA <b>아래</b>에 있습니다.\n"
        "\n"
        "• 기준일: {date}\n"
        "• 52주 신고가 대비 하락률: <b>{drop_pct:.1f}%</b>\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "\n"
        "⚠️ 하락 추세 유지 관망 추천"
    ),
}


_DROP_TEMPLATES: dict[int, str] = {
    10: (
        "🚨 <b>[52주 신고가 대비 10% 하락]</b> QQQ\n"
        "\n"
        "📉 현재가가 52주 신고가 대비 <b>{drop_pct:.1f}% 하락</b>했습니다.\n"
        "\n"
        "• 현재가: <b>{current_price:.2f}</b>\n"
        "• 52주 신고가: <b>{high_52w:.2f}</b>\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "• 기준일: {date}\n"
        "\n"
        "💡 TQQQ 총 보유금의 30% 매수!!"
    ),
    20: (
        "🔥 <b>[52주 신고가 대비 20% 하락]</b> QQQ\n"
        "\n"
        "📉 현재가가 52주 신고가 대비 <b>{drop_pct:.1f}% 하락</b>했습니다.\n"
        "\n"
        "• 현재가: <b>{current_price:.2f}</b>\n"
        "• 52주 신고가: <b>{high_52w:.2f}</b>\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "• 기준일: {date}\n"
        "\n"
        "💡 TQQQ 총 보유금의 30% 추가 매수!!(총 60%)"
    ),
}


def build_message(result: MAResult, state: dict) -> str:
    template = _TEMPLATES[result.signal]
    drop_pct_display = -(result.drop_pct * 100) if result.signal == "below" else result.drop_pct * 100
    message = template.format(
        short_period=result.short_period,
        long_period=result.long_period,
        short_ma=result.short_ma_value,
        long_ma=result.long_ma_value,
        current_price=result.current_price,
        drop_pct=drop_pct_display,
        date=result.today_date,
    )

    # above/below 신호일 때 마지막 매수일 정보 추가
    if result.signal in ("above", "below"):
        buy_date  = state.get("last_golden_cross_date")
        buy_price = state.get("last_golden_cross_price")
        if buy_date:
            message += f"\n\n🗓 마지막 매수일: <b>{buy_date}</b> (매수가: {buy_price:.2f})"

    return message


def _build_drop_message(template: str, result: MAResult) -> str:
    return template.format(
        drop_pct=result.drop_pct * 100,
        current_price=result.current_price,
        high_52w=result.high_52w,
        short_period=result.short_period,
        long_period=result.long_period,
        short_ma=result.short_ma_value,
        long_ma=result.long_ma_value,
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


def notify_ma(ma_result: MAResult, state: dict) -> None:
    """MA 신호 메시지 발송."""
    send_telegram_message(build_message(ma_result, state))


def notify_drop(ma_result: MAResult, level: int) -> None:
    """52주 신고가 대비 하락 알림 발송. level: 10 또는 20"""
    logger.info("52주 고가 대비 %.2f%% 하락 — %d%% 하락 알림 발송", ma_result.drop_pct * 100, level)
    send_telegram_message(_build_drop_message(_DROP_TEMPLATES[level], ma_result))
