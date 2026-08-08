from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)
from analysis.finance_company_analysis.bank_ratio_service import (
    BankRatioCalculationError,
    calculate_bank_ratios,
)


BANK_COMPARISON_RATIO_ORDER = (
    "BANK_ROA",
    "BANK_ROE",
    "BANK_NET_INTEREST_ASSET_RATIO",
    "BANK_NET_FEE_ASSET_RATIO",
    "BANK_LOAN_ASSET_RATIO",
    "BANK_DEPOSIT_LIABILITY_RATIO",
    "BANK_BORROWING_LIABILITY_RATIO",
    "BANK_CREDIT_COST_RATIO",
)

BANK_COMPARISON_RATIO_NAMES = {
    "BANK_ROA": "총자산이익률(은행)",
    "BANK_ROE": "자기자본이익률(은행)",
    "BANK_NET_INTEREST_ASSET_RATIO": "순이자손익/평균자산",
    "BANK_NET_FEE_ASSET_RATIO": "순수수료손익/평균자산",
    "BANK_LOAN_ASSET_RATIO": "대출채권(등) 비중",
    "BANK_DEPOSIT_LIABILITY_RATIO": "예수부채 비중",
    "BANK_BORROWING_LIABILITY_RATIO": "차입부채 비중",
    "BANK_CREDIT_COST_RATIO": "신용손실비용/평균대출채권(등)",
}


class BankCompanyComparisonError(Exception):
    """
    은행·금융지주 비교 분석을 수행할 수 없는 경우 발생한다.
    """


def compare_bank_companies(
    companies: Iterable[dict[str, str]],
    *,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict:
    """
    여러 은행·금융지주의 재무비율을 실제 DB 재무제표에서 계산해 비교한다.

    Parameters
    ----------
    companies:
        corp_code와 corp_name을 가진 dict iterable.
        예:
        {
            "corp_name": "KB금융",
            "corp_code": "00688996",
        }

    Returns
    -------
    dict
        - companies: 기업별 계산 결과
        - rankings: 비율별 순위
        - unavailable_companies: 재무제표가 없어 비교하지 못한 기업
    """
    company_list = list(companies)

    if not company_list:
        raise BankCompanyComparisonError(
            "비교할 금융회사가 없습니다."
        )

    company_results: list[dict[str, Any]] = []
    unavailable_companies: list[dict[str, str]] = []

    for company in company_list:
        corp_code = str(company.get("corp_code") or "").strip()
        corp_name = str(company.get("corp_name") or corp_code).strip()

        if not corp_code:
            unavailable_companies.append(
                {
                    "corp_name": corp_name or "-",
                    "corp_code": "",
                    "reason": "corp_code가 없습니다.",
                }
            )
            continue

        statements = fetch_financial_statements_from_db(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

        if not statements:
            unavailable_companies.append(
                {
                    "corp_name": corp_name,
                    "corp_code": corp_code,
                    "reason": "조건에 해당하는 재무제표가 DB에 없습니다.",
                }
            )
            continue

        try:
            ratios = calculate_bank_ratios(
                statements=statements,
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )
        except BankRatioCalculationError as error:
            unavailable_companies.append(
                {
                    "corp_name": corp_name,
                    "corp_code": corp_code,
                    "reason": str(error),
                }
            )
            continue

        ratio_map = {
            ratio["ratio_code"]: ratio
            for ratio in ratios
        }

        company_results.append(
            {
                "corp_name": corp_name,
                "corp_code": corp_code,
                "ratios": ratio_map,
            }
        )

    rankings = _build_rankings(
        company_results
    )

    return {
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "company_count": len(company_results),
        "companies": company_results,
        "rankings": rankings,
        "unavailable_companies": unavailable_companies,
    }


def _build_rankings(
    company_results: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """
    비율별 기업 순위를 만든다.

    주의
    ----
    순위는 단순 수치 순서일 뿐 '좋고 나쁨'을 의미하지 않는다.
    특히 대출채권 비중, 예수부채 비중, 차입부채 비중,
    신용손실비용 비율은 높거나 낮다는 사실 자체를
    우열로 해석해서는 안 된다.
    """
    rankings: dict[str, list[dict[str, Any]]] = {}

    for ratio_code in BANK_COMPARISON_RATIO_ORDER:
        rows: list[dict[str, Any]] = []

        for company in company_results:
            ratio = company["ratios"].get(
                ratio_code
            )

            if ratio is None:
                continue

            value = ratio.get("ratio_value")

            if value is None:
                continue

            rows.append(
                {
                    "corp_name": company["corp_name"],
                    "corp_code": company["corp_code"],
                    "ratio_code": ratio_code,
                    "ratio_name": ratio.get(
                        "ratio_name",
                        BANK_COMPARISON_RATIO_NAMES.get(
                            ratio_code,
                            ratio_code,
                        ),
                    ),
                    "ratio_value": float(value),
                }
            )

        rows.sort(
            key=lambda row: row["ratio_value"],
            reverse=True,
        )

        for rank, row in enumerate(
            rows,
            start=1,
        ):
            row["rank"] = rank

        rankings[ratio_code] = rows

    return rankings


def format_bank_comparison_table(
    comparison: dict,
) -> str:
    """
    기업별 은행 재무비율을 콘솔에서 보기 쉬운 표 형태의 문자열로 만든다.
    """
    companies = comparison.get("companies", [])

    if not companies:
        return "비교 가능한 금융회사가 없습니다."

    name_width = max(
        12,
        max(
            len(str(company["corp_name"]))
            for company in companies
        ),
    )

    lines = [
        "[은행·금융지주 재무비율 비교]",
        "-" * 126,
        (
            f"{'기업명':<{name_width}}"
            f"{'ROA':>10}"
            f"{'ROE':>10}"
            f"{'순이자/자산':>14}"
            f"{'순수수료/자산':>14}"
            f"{'대출/자산':>12}"
            f"{'예수/부채':>12}"
            f"{'차입/부채':>12}"
            f"{'신용손실/대출':>14}"
        ),
        "-" * 126,
    ]

    for company in companies:
        ratios = company["ratios"]

        lines.append(
            f"{company['corp_name']:<{name_width}}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_ROA')):>10}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_ROE')):>10}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_NET_INTEREST_ASSET_RATIO')):>14}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_NET_FEE_ASSET_RATIO')):>14}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_LOAN_ASSET_RATIO')):>12}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_DEPOSIT_LIABILITY_RATIO')):>12}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_BORROWING_LIABILITY_RATIO')):>12}"
            f"{_format_ratio(_ratio_value(ratios, 'BANK_CREDIT_COST_RATIO')):>14}"
        )

    lines.append("-" * 126)

    unavailable = comparison.get(
        "unavailable_companies",
        [],
    )

    if unavailable:
        lines.append("")
        lines.append("[비교 제외 기업]")

        for row in unavailable:
            lines.append(
                f"- {row['corp_name']} "
                f"({row['corp_code']}): "
                f"{row['reason']}"
            )

    return "\n".join(lines)


def format_bank_rankings(
    comparison: dict,
) -> str:
    """
    비율별 단순 수치 순위를 문자열로 만든다.

    우열 평가가 아니라 비교 편의를 위한 정렬 결과이다.
    """
    rankings = comparison.get("rankings", {})

    lines = [
        "[은행·금융지주 비율별 수치 순위]",
        "※ 단순 수치 순위이며 높고 낮음이 곧 우열을 의미하지 않습니다.",
    ]

    for ratio_code in BANK_COMPARISON_RATIO_ORDER:
        rows = rankings.get(ratio_code, [])

        if not rows:
            continue

        ratio_name = BANK_COMPARISON_RATIO_NAMES.get(
            ratio_code,
            ratio_code,
        )

        lines.append("")
        lines.append(f"[{ratio_name}]")

        for row in rows:
            lines.append(
                f"{row['rank']}. "
                f"{row['corp_name']}: "
                f"{_format_ratio(row['ratio_value'])}"
            )

    return "\n".join(lines)


def _ratio_value(
    ratios: dict[str, dict],
    ratio_code: str,
) -> Any:
    ratio = ratios.get(ratio_code)

    if ratio is None:
        return None

    return ratio.get("ratio_value")


def _format_ratio(value: Any) -> str:
    if value is None:
        return "-"

    return f"{float(value):.2f}%"