# QQQ Alert

나스닥100 ETF(QQQ)의 이동평균선 크로스오버 및 52주 신고가 대비 하락을 감지해 텔레그램으로 알림을 발송하는 봇.
로컬 PC의 Windows 작업 스케줄러로 **월~토 KST 06:00** 자동 실행 (GitHub Actions는 `workflow_dispatch` 수동/백업용으로만 유지).

대상 종목: **KODEX 미국나스닥100 (379810)**

---

## 설치

```bash
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
```

---

## 환경변수 설정

### 로컬 실행 — `.env` 파일

프로젝트 루트에 `.env` 파일을 생성합니다 (`.gitignore`에 포함할 것).

```dotenv
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
POLYGON_API_KEY=your_polygon_api_key
```

| 변수 | 설명 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 발급한 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 알림을 수신할 채팅 ID |
| `POLYGON_API_KEY` | [Polygon.io](https://polygon.io) 무료 플랜 API 키 |

### GitHub Actions — Secrets (백업/수동 실행용)

레포지토리 → Settings → Secrets and variables → Actions에서 아래 3개를 등록합니다.

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `POLYGON_API_KEY`

---

## 실행

```bash
source venv/Scripts/activate

python alert_job.py             # 실제 실행 (API 호출 + 텔레그램 발송)
python test_scenarios.py        # 시나리오 테스트 (API 호출 없음)
python test_scenarios.py 1      # 특정 시나리오만 실행
```

## 로컬 자동 실행 (Windows 작업 스케줄러)

`run_alert.ps1`이 venv의 Python으로 `alert_job.py`를 실행하고 결과를 `logs/alert_YYYYMMDD_HHMMSS.log`에 남긴다.

```powershell
# 작업 스케줄러 등록 (최초 1회, PowerShell)
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\workspace\tqqqAlertBot\run_alert.ps1"' `
    -WorkingDirectory "C:\workspace\tqqqAlertBot"
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday,Saturday -At 06:00AM
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -DontStopOnIdleEnd
Register-ScheduledTask -TaskName "QQQAlert" -Action $action -Trigger $trigger -Settings $settings
```

- 작업 이름: `QQQAlert` (월~토 06:00 KST, 절전 모드는 깨워서 실행하지만 완전 종료 상태면 실행되지 않음)
- 확인: `Get-ScheduledTask -TaskName "QQQAlert" | Get-ScheduledTaskInfo`
- `state.json`은 로컬에서만 갱신되며 git에 자동 커밋되지 않음 (GitHub Actions 실행 시와 다른 점)

## 주요 파일

| 파일 | 역할 |
|---|---|
| `alert_job.py` | 메인 실행 파이프라인 (데이터 수집 → MA 계산 → 알림 발송 → 상태 저장) |
| `data_fetcher.py` | QQQ 종가 수집 — 과거 2년치 일봉은 Polygon.io range API, 당일 최신 종가는 Yahoo Finance |
| `ma_calculator.py` | 이동평균 계산, 크로스오버 신호 감지, 52주 고가 대비 하락률 계산 |
| `notifier.py` | 텔레그램 알림 메시지 템플릿 및 발송 로직 |
| `state_manager.py` | state.json 로드/저장, 상태 플래그 관리 |
| `config.py` | 환경변수 로더 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, POLYGON_API_KEY, SYMBOL, SHORT_MA, LONG_MA) |
| `state.json` | 크로스 발생 이력 및 알림 발송 플래그 영속 저장 (GitHub에 커밋됨) |
| `test_scenarios.py` | 실제 API 호출 없이 더미 MAResult로 텔레그램 메시지 발송 테스트 |
| `run_alert.ps1` | 로컬 자동 실행 래퍼 — venv Python으로 `alert_job.py` 실행 후 `logs/`에 로그 저장 (Windows 작업 스케줄러가 호출) |
| `.github/workflows/qqq_alert.yml` | GitHub Actions 워크플로 정의 (현재는 `workflow_dispatch` 수동/백업 실행만 활성화) |

## 핵심 설정값

| 항목 | 값 | 설명 |
|---|---|---|
| `SHORT_MA` | 3일 | 단기 이동평균 기간 |
| `LONG_MA` | 163일 | 장기 이동평균 기간 |
| `DROP_THRESHOLD_10` | 10% | 52주 고가 대비 1차 하락 기준 |
| `DROP_THRESHOLD_20` | 20% | 52주 고가 대비 2차 하락 기준 |
| `QQQ_RISE_THRESHOLD` | 8% | 골든크로스 매수가 대비 일부 매도 기준 (`notifier.py`에 하드코딩, 환경변수 오버라이드 불가) |

## 신호 타입 (SignalType)

| 신호 | 조건 |
|---|---|
| `golden_cross` | 어제 단기MA ≤ 장기MA AND 오늘 단기MA > 장기MA |
| `dead_cross` | 어제 단기MA ≥ 장기MA AND 오늘 단기MA < 장기MA |
| `above` | 크로스 없이 오늘 단기MA > 장기MA |
| `below` | 크로스 없이 오늘 단기MA ≤ 장기MA |

## 알림 우선순위 (dispatch_notification)

`dead_cross` > `drop 20%` > `drop 10%` > `QQQ 8% 상승` > MA 현황 (`golden_cross` / `above` / `below`)

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

## 제약 및 주의사항

- **Polygon.io 무료 플랜**: 과거 2년치 일봉 데이터 제공. 당일 종가는 처리 지연이 있으므로 Yahoo Finance로 보완
- **Yahoo Finance (당일 종가)**: 장 마감(ET 16:00) 직후 데이터 제공. 미국 공휴일은 코드에서 미고려 — 공휴일 당일 데이터 없음
- **데이터 신선도 재시도**: `fetch_daily_close()`는 최신 거래일 데이터가 없으면 3분 간격으로 최대 3회 재시도 후 구 데이터로 진행 (`data_fetcher.py` `max_retries=4`, `retry_wait_sec=180`)
- **state.json 수동 수정 시**: 실행 환경(로컬/GitHub Actions)마다 별도로 관리되므로 state.json이 상태 유지 수단임. 수동 수정 시 JSON 키 이름과 값 타입(`null` / `bool` / `float`) 엄수
- **로컬 vs GitHub Actions 이중 실행 주의**: 현재는 로컬 작업 스케줄러가 유일한 자동 실행 경로이며, GitHub Actions는 `workflow_dispatch`로 수동 실행 시에도 state.json을 커밋·푸시함. 두 경로를 동시에 자동화하면 state.json 불일치가 발생할 수 있음
- **drop 플래그 초기화 규칙**: `dead_cross` 발생 시 `drop_10_alerted` / `drop_20_alerted`는 초기화되지 않음. 오직 가격 회복(`is_52w_drop_10_alert=False`) 시에만 초기화 (`alert_job.py` 참고)
- **QQQ_RISE_THRESHOLD 변경**: `notifier.py` 상수를 직접 수정해야 함 (환경변수 오버라이드 불가)