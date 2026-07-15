# OpenDART Financial Analyzer (with 생성형 AI)

OpenDART API를 이용하여 기업의 기준정보와 재무제표를 수집하고 SQLite 데이터베이스에 저장한 뒤, 저장된 데이터를 기반으로 재무 분석 기능을 제공하는 Python 프로젝트입니다.

이 프로젝트는 단순히 OpenDART API를 호출하는 수준을 넘어 **Client → Service → Parser → Repository → Database → Analysis** 구조를 적용하여 데이터 수집, 저장, 조회, 분석을 명확히 분리하는 것을 목표로 설계되었습니다.

현재 구현된 주요 기능은 다음과 같습니다.

* OpenDART 공통 API Client
* 기업 고유번호(Corp Code) 동기화
* 기업 정보 저장 및 조회
* 단일회사 전체 재무제표 수집
* 재무제표 Parser
* SQLite 저장 및 중복 방지
* 저장된 재무제표 조회
* 주요 재무비율 계산

향후에는 감사보고서 분석, 기업 간 재무 비교, 생성형 AI를 활용한 감사 관점 분석 기능으로 확장할 계획입니다.

---

# 프로젝트 목적

전자공시시스템(DART)은 기업의 사업보고서, 감사보고서, 재무제표 등 다양한 공시 정보를 제공하지만 실제 분석에 활용하기 위해서는 상당한 전처리 과정이 필요합니다.

본 프로젝트는

* 기업 기준정보 구축
* 재무제표 수집
* 데이터베이스 저장
* 재무 분석
* 향후 감사보고서 분석

까지 하나의 파이프라인으로 구성하여 재무 분석에 활용 가능한 데이터 플랫폼을 구축하는 것을 목표로 합니다.

---

# 시스템 아키텍처

```text
                    OpenDART API
                          │
                          ▼
                     DartClient
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
Corporation Service          Financial Statement Service
         │                                 │
         ▼                                 ▼
 Corporation Parser         Financial Statement Parser
         │                                 │
         ▼                                 ▼
Corporation Repository      Financial Statement Repository
                    │
                    ▼
              SQLite Database
                    │
                    ▼
        Financial Ratio Service
                    │
                    ▼
               CLI / Console
```

---

# 프로젝트 구조

```text
opendart-financial-analyzer/

analysis/
    financial_ratio_service.py

dart/
    client.py
    corporation_service.py
    financial_statement_parser.py
    financial_statement_service.py

database/
    connection.py
    corporation_repository.py
    financial_statement_repository.py
    schema.py

data/
    dart.db

tests/

config.py
main.py
requirements.txt
README.md
```

---

# 주요 기능

## 1. OpenDART API Client

공통 HTTP Client를 통해 OpenDART API 호출을 담당합니다.

지원 기능

* 인증키 자동 포함
* GET 요청 처리
* JSON 응답 처리
* ZIP 다운로드
* HTTP 오류 처리
* OpenDART 상태 코드 검증
* 사용자 정의 예외 처리

---

## 2. 기업 기준정보 동기화

`corpCode.xml`을 이용하여 기업 정보를 동기화합니다.

지원 기능

* XML 다운로드
* ZIP 압축 해제
* XML 파싱
* 신규 기업 저장
* 기존 기업 갱신
* 비활성 기업 관리

저장 정보

* 기업 고유번호
* 기업명
* 종목코드
* 수정일
* 활성 여부
* 최초 확인 시각
* 최근 확인 시각
* 비활성화 시각

---

## 3. 재무제표 수집

OpenDART `fnlttSinglAcntAll.json` API를 이용하여 단일회사 전체 재무제표를 수집합니다.

지원 기능

* 단일회사 전체 재무제표
* 연결(CFS) 재무제표
* 별도(OFS) 재무제표
* 사업보고서
* 반기보고서
* 분기보고서
* JSON 응답 검증
* Parser 기반 정규화

---

## 4. 재무제표 저장

재무제표는 SQLite에 원본 형태를 최대한 유지하여 저장합니다.

주요 저장 컬럼

* rcept_no
* corp_code
* bsns_year
* reprt_code
* fs_div
* sj_div
* account_id
* account_nm
* account_detail
* thstrm_amount
* frmtrm_amount
* currency

동일 공시의 동일 계정은 SQLite UNIQUE 제약조건과 `INSERT OR IGNORE`를 이용하여 중복 저장을 방지합니다.

---

## 5. Repository

### Corporation Repository

* 기업 저장
* 기업 갱신
* 기업 조회
* 전체 기업 조회
* 활성 기업 조회

### Financial Statement Repository

* 재무제표 저장
* 기업별 조회
* 사업연도별 조회
* 보고서별 조회
* 연결/별도 조회
* 특정 계정 조회
* 저장 행 수 조회

---

## 6. 재무제표 조회

저장된 재무제표를 CLI에서 조회할 수 있습니다.

지원 조건

* 기업 고유번호
* 사업연도
* 보고서 코드
* 연결/별도 재무제표

한글 계정명이 긴 경우에도 보기 쉽도록 `wcwidth`를 이용하여 출력 폭을 보정하였습니다.

---

## 7. 재무비율 계산

저장된 재무제표를 기반으로 직접 주요 재무비율을 계산합니다.

현재 지원하는 지표

* 영업이익률
* 순이익률
* ROA
* ROE
* 부채비율
* 유동비율

구현 특징

* 재무제표 원본 데이터를 직접 이용
* 평균 자산·평균 자본을 이용한 ROA·ROE 계산
* 계정명 Alias 지원
* 계산 로직과 출력 로직 분리

---

# 데이터베이스

현재 주요 테이블

## dart_corporations

기업 기준정보 저장

주요 컬럼

* corp_code
* corp_name
* stock_code
* modify_date
* is_active
* first_seen_at
* last_seen_at
* deactivated_at

---

## financial_statements

기업 재무제표 저장

주요 컬럼

* rcept_no
* corp_code
* bsns_year
* reprt_code
* fs_div
* sj_div
* account_id
* account_nm
* account_detail
* thstrm_amount
* frmtrm_amount

---

# 설계 원칙

## 계층 분리

```text
Client
↓

Service
↓

Parser
↓

Repository
↓

Database
↓

Analysis
```

각 계층이 하나의 책임만 가지도록 설계했습니다.

---

## Parser 분리

API 응답을 Repository에 직접 전달하지 않고 Parser를 별도로 두었습니다.

장점

* API 응답 변경 대응
* 저장 구조 변경 영향 최소화
* 테스트 용이성 향상

---

## 원본 데이터 보존

재무제표는 가능한 한 원본 형태를 유지하여 저장합니다.

재무비율은 저장된 데이터를 이용하여 계산하도록 구성했습니다.

---

## 재실행 가능성

동일 데이터를 반복 수집해도 중복 저장되지 않도록 설계했습니다.

---

# 기술 스택

* Python
* OpenDART API
* SQLite
* Requests
* python-dotenv
* pytest
* wcwidth

---

# 테스트

현재 검증 완료

* OpenDART Client
* 기업 동기화
* 재무제표 Parser
* Repository 저장
* Repository 조회
* 재무제표 조회
* 재무비율 계산

---

# 개발 현황

## Phase 1 — 기반 구축

* [x] 프로젝트 구조
* [x] OpenDART Client
* [x] SQLite
* [x] Repository

## Phase 2 — 기업 기준정보

* [x] 기업 고유번호 동기화
* [x] 기업 조회
* [x] 비활성 기업 관리

## Phase 3 — 재무제표

* [x] 단일회사 전체 재무제표 조회
* [x] Parser
* [x] SQLite 저장
* [x] 중복 저장 방지
* [x] 조회 기능

## Phase 4 — 재무 분석

* [x] 주요 계정 추출
* [x] 영업이익률
* [x] 순이익률
* [x] ROA
* [x] ROE
* [x] 부채비율
* [x] 유동비율

## Phase 5 — 향후 계획

* [ ] 기업 검색 기능 고도화
* [ ] 기업 간 재무비율 비교
* [ ] 감사보고서 수집
* [ ] 감사의견 분석
* [ ] 핵심감사사항(KAM) 분석
* [ ] 생성형 AI 기반 감사보고서 분석
* [ ] 재무제표와 감사보고서 연계 분석

---

# 향후 개발 방향

현재 프로젝트는 재무제표를 안정적으로 수집·저장하고 주요 재무비율을 계산하는 단계까지 구현되었습니다.

향후에는 감사보고서의 감사의견, 강조사항 및 핵심감사사항을 수집하고, 생성형 AI를 활용하여 비정형 텍스트에서 관련 재무제표 계정을 추출한 뒤 저장된 재무 데이터와 연결하여 감사 관점의 분석 리포트를 제공하는 기능으로 확장할 계획입니다.

---

# 활용 가능성

* 기업 재무 분석
* 기업 간 재무비율 비교
* 투자 대상 기업 기초 분석
* 감사 위험 분석
* 감사보고서 기반 리스크 식별
* 생성형 AI 기반 회계·감사 데이터 분석
* 회계법인 디지털 감사 포트폴리오

---

# 주의사항

* 본 프로젝트는 학습 및 포트폴리오 목적으로 개발되었습니다.
* OpenDART API 이용 정책을 준수해야 합니다.
* 분석 결과는 투자 권유가 아닌 참고자료입니다.
* 실제 API 인증키는 Git 저장소에 포함하지 않습니다.
