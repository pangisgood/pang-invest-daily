# PANG INVEST DAILY

GitHub Pages에 올려 쓰는 개인 재테크 데일리 대시보드입니다.

## 포함 종목

- TIGER 미국필라델피아반도체나스닥 (381180)
- TIGER 미국배당다우존스 (458730)
- TIGER 미국나스닥100타겟데일리커버드콜 (486290)
- ACE 미국배당퀄리티 (0046Y0)
- TIGER 미국S&P500 (360750)
- KODEX 미국S&P500액티브 (0041E0)
- SOL 국제금 (0066W0)
- KODEX 200액티브 (494890)
- TIME 차이나AI테크액티브 (0043Y0)
- 1Q 은액티브 (0172V0)

시장 지표: USD/KRW, 100JPY/KRW(파생계산), S&P500, NASDAQ, PHLX 반도체, KOSPI, KOSDAQ, 금, 은, Hang Seng TECH.

## 핵심 구조

- API Key 없음
- GitHub Actions가 Yahoo Finance 공개 chart endpoint에서 데이터를 받아 `data.json`을 갱신
- 한국시간 평일 오전 7:10 / 오후 4:10 업데이트 예약
- 보유수량·평균단가는 `localStorage`에만 저장 → 공개 GitHub 코드에 개인 자산정보를 넣지 않음
- 홈 화면 추가용 manifest + service worker 포함

## 배포

1. 새 GitHub 저장소를 만들고 이 폴더 안의 파일을 그대로 업로드합니다.
2. `Actions` 탭 → `Update market data` → `Run workflow`를 한 번 실행합니다.
3. `Settings → Pages` → `Deploy from a branch` → `main / (root)` → Save.
4. 생성된 GitHub Pages 주소를 휴대폰 Chrome에서 열고 `홈 화면에 추가`합니다.

### Actions에서 push 권한 오류가 날 때

`Settings → Actions → General → Workflow permissions`에서 `Read and write permissions`를 선택한 뒤 다시 실행합니다.

## 주의

Yahoo Finance chart endpoint는 API Key가 필요 없지만 공식 유료 API 계약형 인터페이스가 아니므로 향후 형식이 바뀔 수 있습니다. 특정 종목이 일시적으로 실패하면 스크립트는 기존 `data.json` 값을 유지하고 화면에 `이전값 유지`로 표시합니다.
