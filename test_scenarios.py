"""
시나리오별 텔레그램 메시지 발송 테스트.

실제 API 호출 없이 더미 MAResult를 생성해 각 시나리오의 메시지를 확인한다.

실행:
    python test_scenarios.py          # 전체 시나리오
    python test_scenarios.py 1        # 특정 시나리오만 (번호 지정)
"""
import sys
import time
from ma_calculator import MAResult
from notifier import dispatch_notification

# ── 시나리오별 state 정의 ──────────────────────────────────────
STATE_DEFAULT = {
    "last_golden_cross_date": "2026-01-15",
    "last_golden_cross_price": 510.00,
    "last_golden_cross_tqqq_price": 60.00,
    "last_dead_cross_date": None,
    "last_dead_cross_price": None,
    "drop_10_alerted": False,
    "drop_20_alerted": False,
    "tqqq_25_alerted": False,
}

STATE_DROP10_SENT   = {**STATE_DEFAULT, "drop_10_alerted": True,  "drop_20_alerted": False}
STATE_DROP20_SENT   = {**STATE_DEFAULT, "drop_10_alerted": True,  "drop_20_alerted": True}
STATE_TQQQ25_SENT   = {**STATE_DEFAULT, "tqqq_25_alerted": True}

# ── 시나리오 정의 ──────────────────────────────────────────────
SCENARIOS = [
    {
        "no": 1,
        "name": "골든크로스 발생",
        "expected": "골든크로스 메시지",
        "state": STATE_DEFAULT,
        "result": MAResult(
            signal="golden_cross",
            short_ma_value=625.50,
            long_ma_value=618.30,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=628.60,
            high_52w=635.77,
            drop_pct=0.011,
            is_52w_drop_10_alert=False,
            is_52w_drop_20_alert=False,
        ),
    },
    {
        "no": 2,
        "name": "데드크로스 발생",
        "expected": "데드크로스 메시지",
        "state": STATE_DEFAULT,
        "result": MAResult(
            signal="dead_cross",
            short_ma_value=505.10,
            long_ma_value=508.30,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=503.00,
            high_52w=635.77,
            drop_pct=0.21,
            is_52w_drop_10_alert=True,
            is_52w_drop_20_alert=True,
        ),
    },
    {
        "no": 3,
        "name": "단기MA 위 (상승 추세 유지)",
        "expected": "above 메시지",
        "state": STATE_DEFAULT,
        "result": MAResult(
            signal="above",
            short_ma_value=619.02,
            long_ma_value=605.31,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=628.60,
            high_52w=635.77,
            drop_pct=0.011,
            is_52w_drop_10_alert=False,
            is_52w_drop_20_alert=False,
        ),
    },
    # ── below 발송 케이스 4가지 ────────────────────────────────
    {
        "no": "4-1",
        "name": "아래 -drop 10% 발생 전 (drop_pct < 10%)",
        "expected": "below 메시지",
        "state": STATE_DEFAULT,
        "result": MAResult(
            signal="below",
            short_ma_value=500.10,
            long_ma_value=508.30,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=498.00,
            high_52w=510.00,
            drop_pct=0.024,
            is_52w_drop_10_alert=False,
            is_52w_drop_20_alert=False,
        ),
    },
    {
        "no": "4-2",
        "name": "아래 -drop 10% 상황이지만 이미 발송됨",
        "expected": "below 메시지 (drop 알림 없음)",
        "state": STATE_DROP10_SENT,
        "result": MAResult(
            signal="below",
            short_ma_value=500.10,
            long_ma_value=508.30,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=571.00,
            high_52w=635.77,
            drop_pct=0.102,
            is_52w_drop_10_alert=True,
            is_52w_drop_20_alert=False,
        ),
    },
    {
        "no": "4-3",
        "name": "아래 -drop 20% 발생 전 (10~20% 구간, 10% 이미 발송됨)",
        "expected": "below 메시지 (20% 미달성)",
        "state": STATE_DROP10_SENT,
        "result": MAResult(
            signal="below",
            short_ma_value=500.10,
            long_ma_value=508.30,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=540.00,
            high_52w=635.77,
            drop_pct=0.150,
            is_52w_drop_10_alert=True,
            is_52w_drop_20_alert=False,
        ),
    },
    {
        "no": "4-4",
        "name": "아래 -drop 20% 상황이지만 이미 발송됨",
        "expected": "below 메시지 (drop 알림 없음)",
        "state": STATE_DROP20_SENT,
        "result": MAResult(
            signal="below",
            short_ma_value=500.10,
            long_ma_value=508.30,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=508.00,
            high_52w=635.77,
            drop_pct=0.201,
            is_52w_drop_10_alert=True,
            is_52w_drop_20_alert=True,
        ),
    },
    # ── drop 이벤트 ───────────────────────────────────────────
    {
        "no": 5,
        "name": "데드크로스 + 52주 신고가 대비 10% 하락",
        "expected": "데드크로스 메시지 (drop 알림 없음, dead_cross 우선)",
        "state": STATE_DEFAULT,
        "result": MAResult(
            signal="dead_cross",
            short_ma_value=568.00,
            long_ma_value=572.00,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=571.00,
            high_52w=635.77,
            drop_pct=0.102,
            is_52w_drop_10_alert=True,
            is_52w_drop_20_alert=False,
        ),
    },
    {
        "no": 6,
        "name": "52주 신고가 대비 10% 하락 첫 발생",
        "expected": "52주 최고가 대비 10% 하락 메시지",
        "state": STATE_DEFAULT,
        "result": MAResult(
            signal="above",
            short_ma_value=578.00,
            long_ma_value=570.00,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=572.00,
            high_52w=635.77,
            drop_pct=0.100,
            is_52w_drop_10_alert=True,
            is_52w_drop_20_alert=False,
        ),
    },
    {
        "no": 7,
        "name": "52주 신고가 대비 20% 하락 첫 발생",
        "expected": "52주 최고가 대비 20% 하락 메시지",
        "state": STATE_DROP10_SENT,
        "result": MAResult(
            signal="below",
            short_ma_value=505.00,
            long_ma_value=510.00,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=508.00,
            high_52w=635.77,
            drop_pct=0.201,
            is_52w_drop_10_alert=True,
            is_52w_drop_20_alert=True,
        ),
    },
    # ── TQQQ 25% 상승 ─────────────────────────────────────────
    {
        "no": 8,
        "name": "QQQ 8% 이상 상승 첫 발생",
        "expected": "QQQ 8% 상승 메시지 (매도 알림, +24.5%)",
        "state": STATE_DEFAULT,           # last_golden_cross_price=510.00
        "result": MAResult(
            signal="above",
            short_ma_value=630.00,
            long_ma_value=610.00,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=635.00,
            high_52w=638.00,
            drop_pct=0.005,
            is_52w_drop_10_alert=False,
            is_52w_drop_20_alert=False,
        ),
    },
    {
        "no": 9,
        "name": "QQQ 8% 이상 상승이지만 이미 발송됨",
        "expected": "above 메시지 (QQQ 8% 알림 없음)",
        "state": STATE_TQQQ25_SENT,       # tqqq_25_alerted=True
        "result": MAResult(
            signal="above",
            short_ma_value=632.00,
            long_ma_value=612.00,
            today_date="2026-04-14",
            short_period=3,
            long_period=163,
            current_price=637.00,
            high_52w=640.00,
            drop_pct=0.005,
            is_52w_drop_10_alert=False,
            is_52w_drop_20_alert=False,
        ),
    },
]


def run_scenario(scenario: dict) -> None:
    no       = scenario["no"]
    name     = scenario["name"]
    expected = scenario.get("expected", "")
    result   = scenario["result"]
    state    = scenario["state"]
    print(f"\n[{no}] {name}")
    print(f"     기대 결과: {expected}")
    print(f"     테스트 중...")

    dispatch_notification(result, state)

    print(f"     발송 완료")


def main() -> None:
    if len(sys.argv) > 1:
        target = sys.argv[1]
        matched = [s for s in SCENARIOS if str(s["no"]) == target]
        if not matched:
            nos = [str(s["no"]) for s in SCENARIOS]
            print(f"시나리오 {target}번이 없습니다. 가능한 번호: {', '.join(nos)}")
            sys.exit(1)
        run_scenario(matched[0])
    else:
        print(f"전체 {len(SCENARIOS)}개 시나리오 테스트 시작")
        for scenario in SCENARIOS:
            run_scenario(scenario)
            time.sleep(1)
        print("\n전체 테스트 완료")


if __name__ == "__main__":
    main()
