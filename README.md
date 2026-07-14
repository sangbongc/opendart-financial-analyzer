# OpenDART Financial Analyzer (with 생성형 AI)

OpenDART API를 이용하여 기업의 기준정보와 재무제표를 수집하고 SQLite 데이터베이스에 저장한 뒤, 저장된 데이터를 기반으로 재무 분석 기능을 제공하는 Python 프로젝트입니다.

이 프로젝트는 단순히 OpenDART API를 호출하는 수준을 넘어, **Client → Service → Parser → Repository → Database** 구조를 적용하여 데이터 수집과 저장, 조회, 분석을 분리한 구조로 설계되었습니다.

현재는 다음 기능까지 구현되어 있습니다.

* OpenDART 공통 API 클라이언트
* 기업 고유번호(Corp Code) 동기화
* 기업 정보 저장 및 조회
* 단일회사 전체 재무제표 수집
* 재무제표 Parser
* SQLite 저장
* 중복 저장 방지
* 저장된 재무제표 조회

향후에는 저장된 데이터를 기반으로 재무비율 계산, 기업 비교, 위험 공시 분석 기능을 추가할 예정입니다.

---

# 프로젝트 목적

전자공시시스템(DART)은 국내 기업의 사업보고서, 재무제표 및 각종 공시 정보를 제공하지만, 실제 데이터를 활용하기 위해서는 다음과 같은 전처리 과정이 필요합니다.

* 기업 고유번호 관리
* 종목코드와 기업 고유번호 연결
* API 응답 검증
* XML 및 JSON 데이터 파싱
* 로컬 데이터베이스 구축
* 중복 저장 방지
* 재무제표 조회
* 재무비율 계산

본 프로젝트는 이러한 과정을 하나의 데이터 파이프라인으로 구성하여 **재무 분석에 사용할 수 있는 데이터 저장소를 구축하는 것**을 목표로 합니다.

---

# 주요 목표

* OpenDART API 공통 Client 구현
* 기업 정보 동기화
* 기업 정보 Repository 구축
* 재무제표 수집 및 저장
* 재무제표 조회 기능
* 재무비율 분석
* 기업 간 비교
* 위험 공시 분석

---

# 시스템 아키텍처

```text
                OpenDART API
                      │
                      ▼
                 DartClient
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
Corporation Service      Financial Statement Service
        │                           │
        ▼                           ▼
 Corporation Parser      Financial Statement Parser
        │                           │
        ▼                           ▼
Corporation Repository   Financial Statement Repository
                │
                ▼
            SQLite Database
```

각 계층의 역할은 다음과 같습니다.

| 계층         | 역할                |
| ---------- | ----------------- |
| Client     | OpenDART API 호출   |
| Service    | 비즈니스 로직 처리        |
| Parser     | API 응답을 저장 구조로 변환 |
| Repository | SQLite 저장 및 조회    |
| Database   | 데이터 영속화           |

---

# 구현 기능

## 1. OpenDART 공통 Client

OpenDART API와의 통신을 담당하는 공통 HTTP 클라이언트입니다.

### 지원 기능

* 인증키 자동 포함
* GET 요청 처리
* JSON 응답 처리
* ZIP 바이너리 응답 처리
* HTTP 오류 처리
* OpenDART 상태 코드 검증
* 빈 응답 검증
* 사용자 정의 `DartAPIError` 제공

---

## 2. 기업 정보 동기화

OpenDART의 `corpCode.xml` API를 이용하여 전체 기업 목록을 데이터베이스와 동기화합니다.

동기화 과정

1. ZIP 다운로드
2. XML 추출
3. 기업 정보 파싱
4. SQLite 저장
5. 기존 데이터 갱신
6. 누락 기업 비활성화
7. 결과 출력

저장되는 정보

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

OpenDART `fnlttSinglAcntAll.json` API를 이용하여 단일회사의 전체 재무제표를 수집합니다.

### 지원 기능

* 단일회사 전체 재무제표 조회
* 연결(CFS) 재무제표
* 별도(OFS) 재무제표
* 사업보고서
* 반기보고서
* 분기보고서
* JSON 응답 검증
* 재무제표 Parser
* SQLite 저장

---

## 4. 재무제표 Parser

API 응답을 그대로 저장하지 않고 저장 구조에 맞게 변환합니다.

Parser를 별도로 분리한 이유는 다음과 같습니다.

* API 응답 형식과 저장 구조 분리
* Repository의 책임 최소화
* 테스트 용이성 향상
* 향후 OpenDART 응답 변경 대응

---

## 5. SQLite 저장

현재 프로젝트는 다음 두 개의 주요 테이블을 사용합니다.

### dart_corporations

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

### financial_statements

기업 재무제표 저장

주요 컬럼

* rcept_no
* reprt_code
* bsns_year
* corp_code
* fs_div
* sj_div
* account_id
* account_nm
* account_detail
* thstrm_amount
* frmtrm_amount
* currency

동일 공시의 동일 계정은 SQLite의 UNIQUE 제약조건과 `INSERT OR IGNORE`를 이용하여 중복 저장을 방지합니다.

---

## 6. Repository 기능

### Corporation Repository

* 기업 저장
* 기업 갱신
* 기업 조회
* 활성 기업 조회
* 전체 기업 조회
* 비활성 기업 관리

### Financial Statement Repository

* 재무제표 저장
* 기업별 재무제표 조회
* 사업연도별 조회
* 보고서별 조회
* 연결/별도 재무제표 조회
* 특정 계정과목 조회
* 저장 행 수 조회

---

## 7. 재무제표 조회

저장된 재무제표는 Repository를 통해 조회할 수 있습니다.

현재 지원하는 조회 조건

* 기업 고유번호
* 사업연도
* 보고서 코드
* 연결/별도 재무제표

조회 결과는 CLI에서 사람이 읽기 쉽도록 정렬하여 출력하도록 구현하였습니다.

한글 문자열 폭 차이로 인해 발생하는 정렬 문제는 `wcwidth` 라이브러리를 사용하여 개선했습니다.
