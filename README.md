# OpenDART Financial Analyzer (with 생성형 AI)

OpenDART API를 이용하여 기업 기준정보·재무제표·XBRL 법인세
주석·감사보고서를 수집하고 SQLite에 저장한 뒤, 재무비율·계정별
증감률·실효세율·자본구조 등을 분석하는 Python 프로젝트입니다.

단순한 API 호출에 그치지 않고 수집·정규화·저장·조회·분석·표현의 책임을
계층별로 분리했습니다. 초기에는 콘솔 중심으로 기능을 검증한 뒤, 기존
Service·Repository 계층을 재사용하여 PySide6 기반 데스크톱 UI를
추가했습니다. 재무분석에서 발견된 이상수치는 결론이 아니라 추가 검토가
필요한 신호로 보고, 산업 특성·재무제표 주석·감사보고서를 함께 검토할 수
있도록 설계했습니다.

아키텍처 설계와 테스트, 결과 검증은 직접 수행했고 구현에는 생성형 AI를
보조 도구로 활용했습니다.

## 주요 기능

-   기업 고유번호 동기화 및 기업명·종목코드 검색
-   단일회사 전체 재무제표 수집·정규화·저장
    -   연결·별도재무제표
    -   사업·분기·반기보고서
-   주요 재무비율 계산 및 저장·조회
    -   수익성: 매출총이익률·영업이익률·순이익률·ROA·ROE
    -   안정성: 부채비율·유동비율
    -   운전자본:
        재고회전율·DIO·매출채권회전율·DSO·매입채무회전율·DPO·CCC
-   주요 계정 증감액·증감률 계산과 이상징후 스크리닝
-   재무제표·재무비율·계정별 증감률 Prepare 및 Batch Prepare
-   다기업 재무지표 비교 및 기업별 통계 요약
-   단일기업 다년도 시계열 분석 및 지표별 차트 시각화
-   시계열 분석 중 미수집 연도 및 신규 재무비율 누락 자동 감지·재계산
-   실효세율 계산 및 법인세 관련 계정 변동 조회
-   XBRL 기반 법인세비용 주석 주요 구성항목 조회
-   회계상 D/E, 이자부부채 D/E 등 자본구조 분석
-   감사보고서 전문 수집 및 감사의견·KAM·강조사항·기타사항·계속기업 관련
    중요한 불확실성 파싱
-   PySide6 기반 데스크톱 UI
    -   재무제표 조회 및 DART 수집·갱신
    -   재무비율 조회 및 계산·갱신
    -   계정 증감분석
    -   다기업 비교
    -   기업 시계열 분석 및 차트

현재 분석은 재무제표 본문과 법인세 주석 등 정형·반정형 데이터를 기반으로
합니다. 수치상의 변동은 결론이 아니라 추가 검토가 필요한 영역을 선별하는
자료로 활용하며, 실제 원인 분석에는 산업 상황, 거래 구조, 회계정책,
재무제표 주석과 감사보고서를 함께 검토해야 한다는 것을 전제로 합니다.

------------------------------------------------------------------------

## 시스템 구조

``` mermaid
flowchart TD
    A[OpenDART API] --> B[기업 기준정보]
    A --> C[재무제표 JSON / XBRL]
    A --> D[감사보고서 뷰어 HTML]

    B --> B1[Corporation Service] --> R1[(Repository)]
    C --> C1[Financial Statement Service / XBRL Parser] --> R2[(Repository)]
    D --> D1[감사보고서 원문 수집] --> D2[Audit Report Parser]

    D2 --> D3[Audit Opinion Parser]
    D2 --> D4[Audit KAM Parser]
    D2 --> D5[Audit Emphasis Parser]
    D2 --> D6[Audit Other Matter Parser]
    D2 --> D7[Audit Going Concern Parser]

    R1 --> DB[(SQLite Database)]
    R2 --> DB
    D3 --> DB
    D4 --> DB
    D5 --> DB
    D6 --> DB
    D7 --> DB

    DB --> E1[Prepare Service]
    DB --> E2[Financial Ratio Service]
    DB --> E3[Account Change Service]
    DB --> E4[Tax Analysis Service]
    DB --> E5[Capital Structure Analysis]
    DB --> E6[Company Comparison]
    DB --> E7[Company Time Series]
    DB --> E8[Audit Report 조회]

    E1 --> F1[Console]
    E2 --> F1
    E3 --> F1
    E4 --> F1
    E5 --> F1
    E6 --> F1
    E7 --> F1
    E8 --> F1

    E1 --> F2[PySide6 Desktop UI]
    E2 --> F2
    E3 --> F2
    E6 --> F2
    E7 --> F2
```

### 계층별 역할

  -----------------------------------------------------------------------------
  계층                                역할
  ----------------------------------- -----------------------------------------
  Client                              OpenDART API 요청과 공통 응답 처리

  Service                             데이터 수집, 동기화, 계산 흐름 관리

  Parser                              JSON·XML·XBRL·HTML 응답을 내부 처리
                                      형식으로 변환

  Repository                          SQLite 저장 및 조회

  Analysis                            저장 데이터를 이용한
                                      재무·세무·자본구조·기업 비교·시계열 분석

  Audit                               감사보고서 섹션 식별 및
                                      감사의견·KAM·강조사항·기타사항·계속기업
                                      불확실성 파싱

  Console                             사용자 입력, 기능 호출, 결과 출력

  UI                                  PySide6 기반 조회·분석·시각화 인터페이스
  -----------------------------------------------------------------------------

### 설계 방향

콘솔과 UI에서 계산 로직을 각각 구현하지 않고 동일한 Service·Repository
계층을 호출합니다. 따라서 데이터 수집·계산 로직을 수정해도 표현 계층의
변경을 최소화할 수 있습니다.

계정명이 같거나 유사한 항목이 여러 재무제표에 존재하는 경우에는
계정명만으로 값을 선택하지 않고 재무제표 종류, 유동·비유동 여부, 계정
별칭 우선순위 등을 함께 고려합니다. 특히 매출채권·재고자산·매입채무와
같이 유동성 구분이 분석 결과에 영향을 주는 계정은 현재 분석 목적에 맞는
값을 우선 선택하도록 보완했습니다.

------------------------------------------------------------------------

## 프로젝트 구조

``` text
opendart-financial-analyzer/
│
├── analysis/
│   ├── account_selector.py
│   ├── account_change_ratio_service.py
│   ├── financial_ratio_service.py
│   ├── prepare_service.py
│   ├── batch_prepare_service.py
│   ├── company_comparison_service.py
│   ├── company_time_series_service.py
│   ├── capital_structure_service.py
│   ├── effective_tax_rate_service.py
│   ├── tax_account_change_service.py
│   └── income_tax_note_service.py
│
├── audit/
│   ├── audit_report_parser.py
│   ├── audit_opinion_parser.py
│   ├── audit_KAM_parser.py
│   ├── audit_emphasis_parser.py
│   ├── audit_other_matter_parser.py
│   ├── audit_going_concern_parser.py
│   ├── constants.py
│   ├── models.py
│   └── parser_utils.py
│
├── console/
│   ├── controller.py
│   ├── corporation_selector.py
│   └── commands/
│       ├── audit_commands.py
│       ├── corporation_commands.py
│       ├── financial_statement_commands.py
│       ├── financial_ratio_commands.py
│       ├── prepare_commands.py
│       ├── batch_prepare_commands.py
│       ├── comparison_commands.py
│       ├── time_series_commands.py
│       ├── income_tax_note_commands.py
│       └── tax_commands.py
│
├── dart/
│   ├── client.py
│   ├── corporation_service.py
│   ├── financial_statement_service.py
│   ├── financial_statement_parser.py
│   ├── xbrl_file_service.py
│   ├── audit_report_file_service.py
│   └── audit_report_viewer_parser.py
│
├── database/
│   ├── connection.py
│   ├── corporation_repository.py
│   ├── financial_ratio_repository.py
│   ├── financial_statement_repository.py
│   ├── financial_statement_change_repository.py
│   ├── company_comparison_repository.py
│   └── schema.py
│
├── ui/
│   ├── main_window.py
│   ├── widgets/
│   │   ├── corporation_search.py
│   │   └── query_conditions.py
│   └── tabs/
│       ├── financial_statement_tab.py
│       ├── financial_ratio_tab.py
│       ├── account_change_tab.py
│       ├── company_comparison_tab.py
│       └── company_time_series_tab.py
│
├── xbrl/
│   ├── xbrl_instance_parser.py
│   ├── presentation_parser.py
│   ├── xbrl_label_parser.py
│   ├── xbrl_note_table_parser.py
│   └── xbrl_models.py
│
├── data/
│   └── audit_reports/
│
├── tests/
├── config.py
├── main.py
├── utils.py
└── requirements.txt
```

> 감사보고서 원문 수집 방식은 XML 직접 다운로드에서 DART 감사보고서
> 뷰어의 HTML·JavaScript 렌더링 구조를 페이지 단위로 순회하며 조각을
> 모아 전문을 조립하는 방식으로 변경했습니다. 이는 XML 다운로드 방식의
> 안정성 문제를 개선하기 위한 것입니다.

------------------------------------------------------------------------

## 재무비율 분석

현재 재무비율 계산은 단순 기말잔액뿐 아니라 필요한 경우 기초·기말
평균잔액을 사용합니다.

  -----------------------------------------------------------------------
  구분                                지표
  ----------------------------------- -----------------------------------
  수익성                              매출총이익률, 영업이익률, 순이익률,
                                      ROA, ROE

  안정성                              부채비율, 유동비율

  운전자본                            재고회전율, DIO, 매출채권회전율,
                                      DSO, 매입채무회전율, DPO, CCC
  -----------------------------------------------------------------------

매출총이익률은 `매출액 - 매출원가`로 매출총이익을 산출한 뒤 매출액으로
나누어 계산합니다. 직접 공시된 매출총이익 계정에 의존하지 않아 기업별
표시 방식 차이에 따른 영향을 줄였습니다.

기업 시계열 분석에서는 현재 정의된 재무비율과 DB에 저장된 `ratio_code`를
비교합니다. 새 재무비율이 추가되어 과거 연도에 해당 계산 결과가 없으면
이를 자동으로 감지하여 재계산할 수 있습니다. 반면 계산 결과가 `NULL`인
경우에는 계산 자체는 수행된 것으로 구분하여 불필요한 반복 처리를
방지합니다.

------------------------------------------------------------------------

## 기업 비교 및 시계열 분석

### 다기업 비교

동일 사업연도·보고서 조건에서 여러 기업의 재무비율과 주요 계정 증감률을
한 번에 비교합니다.

-   수익성·안정성·운전자본 지표 비교
-   매출·매출원가·영업이익·매출채권·재고·매입채무·유형자산 증감률 비교
-   평균·중앙값·표준편차·최솟값·최댓값 요약
-   지표별 정렬
-   계정 선택 우선순위를 적용하여 동일·유사 계정 중 분석 목적에 맞는 값
    선택

산업 간 또는 동일 산업 내 기업 비교에서는 수치의 높고 낮음을 곧바로
우열로 해석하지 않고, 기업의 사업모델과 가치사슬 차이를 함께 검토하는
것을 전제로 합니다.

### 단일기업 시계열

한 기업을 여러 사업연도에 걸쳐 조회하여 재무비율과 주요 계정 변동을
추적합니다.

-   조회 시작연도·종료연도 지정
-   수익성·안정성, 운전자본, 주요 계정 증감률을 구분하여 표시
-   선택 지표의 연도별 추이를 선형 차트로 시각화
-   조회 범위 중 자료가 없는 연도 자동 식별
-   신규 재무비율 추가 후 과거 DB에 해당 `ratio_code`가 없는 연도 자동
    식별
-   누락 자료 준비 후 즉시 재조회 및 화면 갱신

------------------------------------------------------------------------

## 자본구조 분석

재무상태표를 기반으로 회계상 부채와 이자부부채를 구분하여 자본구조를
분석합니다.

-   부채총계 / 자본총계
-   회계상 Debt-to-Equity
-   단기차입금·유동성장기부채·사채·장기차입금 등 이자부부채 식별
-   이자부부채 / 자본총계
-   총부채 중 이자부부채 비중

이 분석은 향후 시장자료에서 계산한 Levered Beta와 결합하여 Unlevered
Beta를 산출하고, WACC·기업가치 평가로 확장하기 위한 기초 데이터로 활용할
수 있도록 구성했습니다.

------------------------------------------------------------------------

## PySide6 데스크톱 UI

기존 콘솔 기능을 대체하기보다, 검증된 Service·Repository 계층 위에
별도의 표현 계층으로 UI를 추가했습니다.

현재 UI에서는 다음 기능을 사용할 수 있습니다.

-   기업 검색 및 선택
-   사업연도·보고서·연결/별도 조건 공유
-   재무제표 DB 조회 및 DART 수집·갱신
-   재무비율 DB 조회 및 계산·갱신
-   주요 계정 증감분석
-   여러 기업 비교
-   한 기업의 다년도 시계열 분석
-   선택 지표 차트 시각화
-   누락 연도 및 신규 비율 계산 결과 자동 준비

이 구조를 통해 콘솔에서 먼저 검증한 분석 기능을 별도 계산 로직 없이
UI에서도 재사용할 수 있습니다.

------------------------------------------------------------------------

## 설치 및 실행

``` bash
git clone https://github.com/sangbongc/opendart-financial-analyzer.git
cd opendart-financial-analyzer
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # DART_API_KEY 입력 (Windows: copy .env.example .env)
python main.py
```

## 기술 스택

Python · OpenDART API · SQLite · Requests · python-dotenv · PySide6 ·
QtCharts · pytest · wcwidth

## 테스트

``` bash
pytest
```

Mock 기반 단위 테스트와 Repository 테스트를 이용하여 외부 API 호출에
의존하지 않고 핵심 로직의 파싱·계산·저장·조회 동작을 검증합니다.

------------------------------------------------------------------------

## 개발 현황

  Phase   내용                                                 상태
  ------- ---------------------------------------------------- ------
  1       프로젝트 기반 구축(Client, SQLite, Repository)       완료
  2       기업 기준정보 동기화·검색                            완료
  3       재무제표 수집·저장·조회                              완료
  4       주요 재무비율 계산·저장·조회                         완료
  5       계정별 증감액·증감률 및 이상징후 스크리닝            완료
  6       실효세율·법인세 계정 분석 및 XBRL 법인세 주석 파싱   완료
  7       Prepare·Batch Prepare 및 콘솔 명령 구조 개선         완료
  8       감사보고서 수집·파싱 및 종합 조회                    완료
  9       산업별·다기업 비교 분석 및 계정 선택 로직 개선       완료
  10      운전자본 회전율·회전일수·CCC 분석 확장               완료
  11      단일기업 다년도 시계열 분석                          완료
  12      PySide6 기반 데스크톱 UI 구축                        완료
  13      회계상·이자부부채 기준 자본구조 분석                 완료
  14      신규 재무비율 누락 감지 및 과거 데이터 재계산        완료

### 향후 계획

-   회계이익-법인세비용 조정표 등 법인세 주석 분석 확장
-   감사보고서(KAM)와 재무분석 결과 연계
-   산업별 통계 기반 이상징후 탐지
-   정정공시 자동 반영
-   Levered/Unlevered/Relevered Beta 분석 연계
-   WACC 및 DCF·상대가치 평가로 분석 범위 확장

------------------------------------------------------------------------

## 활용 가능성

기업 재무상태 기초 분석 · 산업별/다기업 비교 · 단일기업 시계열 분석 ·
재무비율 및 계정 변동 스크리닝 · 운전자본 분석 · 자본구조 분석 ·
실효세율 및 법인세 주석 분석 · 감사보고서(KAM·강조사항·계속기업 관련
중요 불확실성 등) 조회 · 재무분석과 감사보고서를 연계한 이상수치 검토 ·
회계·감사·세무 데이터 분석 포트폴리오

## 주의사항

-   학습 및 포트폴리오 목적으로 개발했으며, 투자 권유·세무 자문·회계감사
    의견을 의미하지 않습니다.
-   계정 변동률이 크다는 것이 곧바로 회계 오류나 위험을 뜻하지 않으며,
    산업 상황·거래 구조·회계정책·주석을 함께 검토해야 합니다.
-   산업별 기업 비교에서 재무비율의 단순 순위는 기업의 우열을 의미하지
    않습니다.
-   일부 기업·산업에서는 매출원가나 특정 운전자본 계정의 표시 방식이
    달라 일부 비율을 계산할 수 없을 수 있습니다.
-   실효세율·이연법인세 변동은 총액 기준 스크리닝 결과이며, 원인
    분석에는 주석 상세 내역이 필요합니다.
-   감사보고서 뷰어 페이지 구조 변경 시 수집 로직이 영향을 받을 수
    있습니다.
-   실제 OpenDART API 인증키는 저장소에 포함하지 않습니다.
