from __future__ import annotations

from typing import Any

from analysis.account_change_ratio_service import (
    AccountChangeRatioError,
    calculate_and_save_account_change_ratios,
)
from analysis.financial_ratio_service import (
    FinancialRatioCalculationError,
    calculate_and_save_financial_ratios,
)
from dart.financial_statement_service import (
    sync_financial_statements,
)


class PrepareFinancialDataError(Exception):
    """
    재무 분석 데이터 준비 과정에서 발생하는 오류.

    stage에는 오류가 발생한 단계가 저장된다.

    - financial_statements
    - financial_ratios
    - account_changes
    """

    def __init__(
        self,
        message: str,
        stage: str,
    ) -> None:
        super().__init__(message)
        self.stage = stage


def prepare_financial_data(
    corp_code: str,
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
) -> dict[str, Any]:
    """
    한 기업의 재무 분석용 데이터를 순서대로 준비한다.

    처리 순서
    ----------
    1. DART 재무제표 수집 및 저장
    2. 저장된 재무제표 기반 재무비율 계산 및 저장
    3. 저장된 재무제표 기반 계정별 증감률 계산 및 저장

    재무비율과 증감률은 1단계에서 저장된 재무제표를
    기준으로 계산하므로 반드시 위 순서를 유지한다.

    Returns
    -------
    dict
        각 단계의 처리 결과와 전체 요약을 반환한다.
    """
    _validate_prepare_conditions(
        corp_code=corp_code,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
    )

    try:
        statement_result = sync_financial_statements(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    except Exception as error:
        raise PrepareFinancialDataError(
            message=(
                "재무제표 수집 및 저장 중 "
                f"오류가 발생했습니다: {error}"
            ),
            stage="financial_statements",
        ) from error

    try:
        ratio_result = calculate_and_save_financial_ratios(
            corp_code=corp_code,
            bsns_year=bsns_year,
            reprt_code=reprt_code,
            fs_div=fs_div,
        )

    except FinancialRatioCalculationError as error:
        raise PrepareFinancialDataError(
            message=f"재무비율 계산 실패: {error}",
            stage="financial_ratios",
        ) from error

    except Exception as error:
        raise PrepareFinancialDataError(
            message=(
                "재무비율 계산 및 저장 중 "
                f"오류가 발생했습니다: {error}"
            ),
            stage="financial_ratios",
        ) from error

    try:
        change_results = (
            calculate_and_save_account_change_ratios(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )
        )

    except AccountChangeRatioError as error:
        raise PrepareFinancialDataError(
            message=f"계정별 증감률 계산 실패: {error}",
            stage="account_changes",
        ) from error

    except Exception as error:
        raise PrepareFinancialDataError(
            message=(
                "계정별 증감률 계산 및 저장 중 "
                f"오류가 발생했습니다: {error}"
            ),
            stage="account_changes",
        ) from error

    return {
        "corp_code": corp_code,
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "financial_statements": statement_result,
        "financial_ratios": ratio_result,
        "account_changes": {
            "calculated_count": len(change_results),
            "saved_count": len(change_results),
            "results": change_results,
        },
        "summary": {
            "received_statement_count": statement_result[
                "received_count"
            ],
            "saved_statement_count": statement_result[
                "saved_count"
            ],
            "ignored_statement_count": statement_result.get(
                "ignored_count",
                statement_result["received_count"]
                - statement_result["saved_count"],
            ),
            "calculated_ratio_count": ratio_result[
                "calculated_count"
            ],
            "saved_ratio_count": ratio_result[
                "saved_count"
            ],
            "calculated_change_count": len(change_results),
        },
    }


def _validate_prepare_conditions(
    corp_code: str,
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
) -> None:
    """
    데이터 준비에 필요한 입력값을 검증한다.
    """
    if not corp_code:
        raise ValueError(
            "corp_code는 비어 있을 수 없습니다."
        )

    if not (
        len(bsns_year) == 4
        and bsns_year.isdigit()
    ):
        raise ValueError(
            "bsns_year는 4자리 숫자여야 합니다."
        )

    if not reprt_code:
        raise ValueError(
            "reprt_code는 비어 있을 수 없습니다."
        )

    if fs_div not in {"CFS", "OFS"}:
        raise ValueError(
            "fs_div는 CFS 또는 OFS여야 합니다."
        )