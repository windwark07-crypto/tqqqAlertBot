# 테스트 시나리오 정의

## 알림 우선순위

`dead_cross` > `drop 20%` > `drop 10%` > `QQQ 8% 상승` > MA 현황 (`above` / `below`)

## State 초기값 정의

| 변수명 | 설명 |
|---|---|
| `STATE_DEFAULT` | 기본 상태. `last_golden_cross_price=510.00`, 모든 알림 플래그 False |
| `STATE_DROP10_SENT` | 10% 하락 알림 발송 완료 (`drop_10_alerted=True`) |
| `STATE_DROP20_SENT` | 10%/20% 하락 알림 모두 발송 완료 (`drop_10_alerted=True`, `drop_20_alerted=True`) |
| `STATE_QQQ8PCT_SENT` | QQQ 8% 상승 알림 발송 완료 (`qqq_8pct_alerted=True`) |

## 시나리오 목록

| No | 시나리오명 | signal | 주요 조건 | 초기 state | 기대 결과 |
|---|---|---|---|---|---|
| 1 | 골든크로스 발생 | `golden_cross` | drop_pct=1.1% | DEFAULT | 골든크로스 메시지 |
| 2 | 데드크로스 발생 | `dead_cross` | drop_pct=21% (drop 무시) | DEFAULT | 데드크로스 메시지 |
| 3 | 단기MA 위 (매수가 대비 8% 미만) | `above` | current=520.00, 상승률=2.0% | DEFAULT | above 메시지 |
| 4-1 | drop 10% 발생 전 | `below` | drop_pct=2.4% | DEFAULT | below 메시지 |
| 4-2 | drop 10% 상황이지만 이미 발송됨 | `below` | drop_pct=10.2%, `drop_10_alerted=True` | DROP10_SENT | below 메시지 |
| 4-3 | drop 10~20% 구간, 10% 이미 발송됨 | `below` | drop_pct=15.0%, `drop_10_alerted=True` | DROP10_SENT | below 메시지 |
| 4-4 | drop 20% 상황이지만 이미 발송됨 | `below` | drop_pct=20.1%, `drop_20_alerted=True` | DROP20_SENT | below 메시지 |
| 5 | 데드크로스 + drop 10% 동시 발생 | `dead_cross` | drop_pct=10.2% (drop 무시) | DEFAULT | 데드크로스 메시지 |
| 6 | drop 10% 첫 발생 | `above` | drop_pct=10.0%, `drop_10_alerted=False` | DEFAULT | 52주 최고가 대비 10% 하락 메시지 |
| 7 | drop 20% 첫 발생 | `below` | drop_pct=20.1%, `drop_10_alerted=True` | DROP10_SENT | 52주 최고가 대비 20% 하락 메시지 |
| 8 | QQQ 8% 이상 상승 첫 발생 | `above` | current=635.00, 상승률=24.5%, `qqq_8pct_alerted=False` | DEFAULT | QQQ 8% 상승 메시지 |
| 9 | QQQ 8% 이상 상승이지만 이미 발송됨 | `above` | current=637.00, 상승률=24.9%, `qqq_8pct_alerted=True` | QQQ8PCT_SENT | above 메시지 |

## 검토 주의사항

- **시나리오 6**: 상승률 12.1%로 QQQ 8% 조건도 해당되지만, `drop_10` 체크가 먼저 실행되므로 10% 하락 메시지 발송
- **시나리오 2, 5**: drop 조건이 함께 존재하지만 `dead_cross` 최우선으로 처리
- **시나리오 3 vs 9**: 시나리오 3은 상승률이 8% 미만인 케이스, 시나리오 9는 이미 발송된 케이스로 구분
