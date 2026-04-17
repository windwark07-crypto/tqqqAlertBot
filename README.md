# QQQ Alert

나스닥100 ETF(QQQ)의 이동평균선 크로스오버 및 52주 신고가 대비 하락을 감지해 텔레그램으로 알림을 발송하는 봇.
GitHub Actions로 **월~토 KST 07:30** 자동 실행.

대상 종목: **KODEX 미국나스닥100 레버리지(합성 H) (409820)**

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

### GitHub Actions — Secrets

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
