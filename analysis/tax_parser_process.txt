XBRL 법인세 주석 파싱 개발 과정
1단계. OpenDART JSON API의 한계 확인

기존 프로젝트에서는 OpenDART의

fnlttSinglAcntAll

API를 이용하여

재무제표
재무비율
주요계정 변동
실효세율

등을 계산하였다.

하지만 여기서 얻을 수 있는 것은

재무제표 숫자

뿐이었다.

예를 들어

법인세비용
4,274,666

은 알 수 있지만,

왜

당기법인세
8,951,271

이연법인세
-5,037,018

이 되었는지는 알 수 없었다.

즉,

법인세비용의 구성내역이나 실효세율 조정표는 JSON API에서 제공하지 않았다.

2단계. XBRL 다운로드

OpenDART가 제공하는

document.xml

API를 이용하여

기업 공시의 XBRL ZIP 파일을 다운로드하였다.

ZIP 안에는

.xbrl
.xsd
_pre.xml
_lab.xml

등의 파일이 포함되어 있음을 확인하였다.

3단계. XBRL 인스턴스 탐색

가장 먼저

entity00126380_2025-12-31.xbrl

을 읽었다.

ElementTree로 XML을 파싱한 뒤

root

를 확인하였다.

약 7,000개의 element가 존재한다는 것을 확인하였다.

4단계. Tax 태그 탐색

처음에는

if "tax" in tag:

방식으로 탐색하였다.

그러나

namespace에도

taxonomy

라는 문자열이 포함되어 있었기 때문에

거의 모든 element가 검색되는 문제가 발생하였다.

5단계. Local Tag 추출

이를 해결하기 위해

tag.split("}")[-1]

을 이용하여

namespace를 제거한

실제 태그명만 추출하였다.

이후

AccountingProfit

CurrentTaxExpenseIncome

DeferredTaxExpenseIncome

IncomeTaxExpenseContinuingOperations

등의 핵심 Tax Fact를 찾을 수 있었다.

6단계. Context 분석

동일한 태그가 여러 번 등장하는 이유를 조사하였다.

예를 들어

IncomeTaxExpenseContinuingOperations

이

여러 개 존재하였다.

원인은

CFY2025

PFY2024

BPFY2023

ConsolidatedMember

SeparateMember

등의

context가 서로 달랐기 때문이었다.

7단계. Context 필터링

우선

CFY2025

ConsolidatedMember

만 남기도록 필터링하였다.

이를 통해

현재 연결재무제표 기준의 Fact만 추출할 수 있게 되었다.

예를 들어

AccountingProfit

TaxExpenseIncomeAtApplicableTaxRate

CurrentTaxExpenseIncome

DeferredTaxExpenseIncome

등을 안정적으로 얻을 수 있었다.

8단계. XBRL 구조 탐색

Fact만으로는

법인세 주석 전체를 재현하기 어렵다고 판단하였다.

따라서

_pre.xml

을 조사하였다.

여기에는

presentation role

이 존재하며

재무제표와 주석의 표시 구조를 정의한다는 것을 확인하였다.

9단계. IAS12 Role 발견

Presentation Role을 출력한 결과

ias_12_role-D835110

ias_12_role-D835115

가 존재하였다.

IAS12는

국제회계기준

Income Taxes

주석에 해당한다.

따라서

법인세 관련 주석은

이 두 Role 아래에 존재함을 확인하였다.

10단계. Role 내부 구조 확인

IAS12 Role 내부의 concept를 출력하였다.

그 결과

주석 하나 안에도

여러 개의 Table이 존재한다는 사실을 확인하였다.

예를 들어

MajorComponentsOfTaxExpenseIncomeTable

ReconciliationOfAccountingProfitMultipliedByApplicableTaxRatesTable

DisclosureOfTemporaryDifferenceUnusedTaxLossesAndUnusedTaxCreditsTable

ExpectedRealisationTimingOfDeferredTaxTable

등이 존재하였다.

이는 하나의 법인세 주석 안에서도

법인세비용 구성
실효세율 조정
이연법인세
미사용 결손금
실현예정시기

등이 각각 별도의 표로 관리된다는 의미였다.

현재까지의 결론

지금까지의 탐색을 통해 XBRL의 계층 구조를 다음과 같이 이해하게 되었다.

XBRL ZIP
│
├── instance (.xbrl)
│      ↓
│      실제 Fact
│
├── presentation (.pre)
│      ↓
│      Role
│          ↓
│          Table
│              ↓
│              LineItems
│                  ↓
│                  Fact
│
├── label (.lab)
│      ↓
│      한글 표시명
│
└── schema (.xsd)
       ↓
       사용자 정의 태그