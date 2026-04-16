# QQQ Alert 프로젝트

## 프로젝트 개요

나스닥100 ETF(QQQ)의 이동평균선 크로스오버 및 52주 신고가 대비 하락을 감지해 텔레그램으로 알림을 발송하는 봇.
GitHub Actions로 매일 KST 07:00(UTC 22:00)에 자동 실행된다.

대상 종목: **KODEX 미국나스닥100 레버리지(합성 H) (409820)**

## 주요 파일

| 파일 | 역할 |
|---|---|
| `alert_job.py` | 메인 실행 파이프라인 (데이터 수집 → MA 계산 → 알림 발송 → 상태 저장) |
| `data_fetcher.py` | Polygon.io API로 QQQ 종가 수집 (2년치 일봉) |
| `ma_calculator.py` | 이동평균 계산, 크로스오버 신호 감지, 52주 고가 대비 하락률 계산 |
| `notifier.py` | 텔레그램 알림 메시지 템플릿 및 발송 로직 |
| `state_manager.py` | state.json 로드/저장, 상태 플래그 관리 |
| `config.py` | 환경변수 로더 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, SYMBOL, SHORT_MA, LONG_MA) |
| `state.json` | 크로스 발생 이력 및 알림 발송 플래그 영속 저장 (GitHub에 커밋됨) |
| `test_scenarios.py` | 실제 API 호출 없이 더미 MAResult로 텔레그램 메시지 발송 테스트 |
| `.github/workflows/qqq_alert.yml` | GitHub Actions 스케줄 실행 정의 |

## 핵심 설정값

| 항목 | 값 | 설명 |
|---|---|---|
| `SHORT_MA` | 3일 | 단기 이동평균 기간 |
| `LONG_MA` | 163일 | 장기 이동평균 기간 |
| `DROP_THRESHOLD_10` | 10% | 52주 고가 대비 1차 하락 기준 |
| `DROP_THRESHOLD_20` | 20% | 52주 고가 대비 2차 하락 기준 |
| `QQQ_RISE_THRESHOLD` | 8% | 골든크로스 매수가 대비 일부 매도 기준 |

## 신호 타입 (SignalType)

| 신호 | 조건 |
|---|---|
| `golden_cross` | 어제 단기MA ≤ 장기MA AND 오늘 단기MA > 장기MA |
| `dead_cross` | 어제 단기MA ≥ 장기MA AND 오늘 단기MA < 장기MA |
| `above` | 크로스 없이 오늘 단기MA > 장기MA |
| `below` | 크로스 없이 오늘 단기MA ≤ 장기MA |

## 알림 우선순위 (dispatch_notification)

`dead_cross` > `drop 20%` > `drop 10%` > `QQQ 8% 상승` > MA 현황 (`above` / `below`)

## state.json 구조

```json
{
  "last_golden_cross_date": "YYYY-MM-DD 또는 null",
  "last_golden_cross_price": "골든크로스 당일 QQQ 종가 또는 null",
  "last_dead_cross_date": "YYYY-MM-DD 또는 null",
  "last_dead_cross_price": "데드크로스 당일 QQQ 종가 또는 null",
  "drop_10_alerted": "10% 하락 알림 발송 여부 (가격 회복 시 초기화)",
  "drop_20_alerted": "20% 하락 알림 발송 여부 (가격 회복 시 초기화)",
  "qqq_8pct_alerted": "QQQ 8% 상승 알림 발송 여부 (데드크로스 시 초기화)"
}
```

## 실행 방법

```bash
# 로컬 테스트 (venv 필수)
source venv/Scripts/activate
python test_scenarios.py        # 전체 시나리오
python test_scenarios.py 1      # 특정 시나리오만
python alert_job.py             # 실제 실행
```

## 테스트 시나리오

테스트 시나리오 정의는 TEST_SCENARIOS.md를 참고할 것.

## 커밋 규칙

- 커밋은 논리적 작업 단위로 분리해서 생성할 것 (예: 기능 변경, 문서 추가, 버그 수정을 각각 별도 커밋)
- 커밋 메시지는 해당 작업을 한 줄로 간결하게 설명할 것 (예: `QQQ 8% 상승 조건으로 변경`, `프로젝트 문서 추가`)
