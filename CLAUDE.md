# QQQ Alert 프로젝트

## 프로젝트 개요

나스닥100 ETF(QQQ)의 이동평균선 크로스오버 및 52주 신고가 대비 하락을 감지해 텔레그램으로 알림을 발송하는 봇.
GitHub Actions로 월~토 KST 07:30(UTC 22:30)에 자동 실행된다.

대상 종목: **KODEX 미국나스닥100 레버리지(합성 H) (409820)**

## 실행 방법

```bash
# 로컬 테스트 (venv 필수)
source venv/Scripts/activate
python test_scenarios.py        # 전체 시나리오
python test_scenarios.py 1      # 특정 시나리오만
python alert_job.py             # 실제 실행
```

## 테스트 시나리오

테스트 시나리오 정의는 `.claude/rules/TEST_SCENARIOS.md`를 참고할 것.

## 커밋 규칙
- 커밋 생성 전 항상 확인 요청할 것
- 커밋은 논리적 작업 단위로 분리해서 생성할 것 (예: 기능 변경, 문서 추가, 버그 수정을 각각 별도 커밋)
- 커밋 메시지는 해당 작업을 한 줄로 간결하게 설명할 것 (예: `QQQ 8% 상승 조건으로 변경`, `프로젝트 문서 추가`)
