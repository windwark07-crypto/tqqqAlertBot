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
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "• 기준일: {date}\n"
        "\n"
        "💡 TQQQ 시가 매수!!"
    ),
    "dead_cross": (
        "🔴 <b>[데드크로스 발생]</b> QQQ\n"
        "\n"
        "📉 {short_period}일 MA가 {long_period}일 MA를 <b>아래로 돌파</b>했습니다!\n"
        "\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "• 기준일: {date}\n"
        "\n"
        "⚠️ TQQQ 시가 매도!!"
    ),
    "above": (
        "🔵 <b>[MA 현황]</b> QQQ\n"
        "\n"
        "📊 {short_period}일 MA가 {long_period}일 MA <b>위</b>에 있습니다.\n"
        "\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "• 기준일: {date}\n"
        "\n"
        "✅ 상승 추세 유지 중 홀딩 추천"
    ),
    "below": (
        "⚫ <b>[MA 현황]</b> QQQ\n"
        "\n"
        "📊 {short_period}일 MA가 {long_period}일 MA <b>아래</b>에 있습니다.\n"
        "\n"
        "• {short_period}일 MA: <b>{short_ma:.2f}</b>\n"
        "• {long_period}일 MA: <b>{long_ma:.2f}</b>\n"
        "• 기준일: {date}\n"
        "\n"
        "⚠️ 하락 추세 주의 관망 추천"
    ),
}


def build_message(result: MAResult) -> str:
    template = _TEMPLATES[result.signal]
    return template.format(
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


def notify(ma_result: MAResult) -> None:
    message = build_message(ma_result)
    send_telegram_message(message)
