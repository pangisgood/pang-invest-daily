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
별도 유료 API나 API Key 없이 구성

• API Key 없음

• 네이버 금융의 공개 시세·차트 데이터를 활용
  - 국내 ETF 현재가 및 과거 시세
  - KOSPI, KOSDAQ
  - S&P500, NASDAQ, PHLX 반도체 등 주요 해외지수
  - 원달러 환율, 금, 은 등 주요 시장지표
• Python의 update_data.py가 데이터를 수집하고 가공
  - 현재가
  - 1일, 7일, 30일 변화율
  - 최근 가격 이력
  - 종목별 기본 정보
  등을 계산해서 data.json으로 저장
• GitHub Actions가 update_data.py를 정기적으로 자동 실행
  - 수동 실행 가능
  - 정해진 시간에 자동 실행
  - data.json이 갱신되면 GitHub에 자동 Commit
• GitHub Pages의 index.html이 data.json을 읽어서 화면 구성
  - 현재가
  - 1D / 7D / 30D 변화율
  - 최근 가격 추이 그래프
  - 시장지표
  - 내 보유자산과 연결한 ‘오늘 체크’ 영역 표시
• 보유수량과 평균단가는 localStorage에만 저장
  - Public GitHub Repository에는 개인 자산정보를 넣지 않음
  - 현재 사용 중인 브라우저에만 저장
  - 이를 바탕으로 평가금액, 손익, 수익률 계산 가능
• manifest + service worker 적용
  - 휴대폰 홈 화면에 추가 가능
  - 일반 앱처럼 바로 실행 가능
  - 단, 수정 배포 후 이전 파일이 캐시에 남을 수 있어 캐시 갱신도 고려 필요


[전체 흐름]
네이버 금융 공개 데이터
        ↓
Python update_data.py
데이터 수집·계산
        ↓
data.json 생성
        ↑
GitHub Actions
정기 자동 실행
        ↓
GitHub Repository
        ↓
GitHub Pages
        ↓
HTML + JavaScript
        ↓
PANG INVEST DAILY

보유수량·평균단가
        ↓
localStorage
        ↓
현재 브라우저에만 저장

## 배포

1. 새 GitHub 저장소를 만들고 이 폴더 안의 파일을 그대로 업로드합니다.
2. `Actions` 탭 → `Update market data` → `Run workflow`를 한 번 실행합니다.
3. `Settings → Pages` → `Deploy from a branch` → `main / (root)` → Save.
4. 생성된 GitHub Pages 주소를 휴대폰 Chrome에서 열고 `홈 화면에 추가`합니다.

### Actions에서 push 권한 오류가 날 때

`Settings → Actions → General → Workflow permissions`에서 `Read and write permissions`를 선택한 뒤 다시 실행합니다.

## 주의

Yahoo Finance chart endpoint는 API Key가 필요 없지만 공식 유료 API 계약형 인터페이스가 아니므로 향후 형식이 바뀔 수 있습니다. 특정 종목이 일시적으로 실패하면 스크립트는 기존 `data.json` 값을 유지하고 화면에 `이전값 유지`로 표시합니다.
