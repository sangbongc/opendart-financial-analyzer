from __future__ import annotations

from concurrent.futures import (
    Future,
    ThreadPoolExecutor,
    as_completed,
)
from time import sleep
from typing import Any

from analysis.account_change_ratio_service import (
    calculate_and_save_account_change_ratios,
)
from analysis.financial_ratio_service import (
    calculate_and_save_financial_ratios,
)
from dart.financial_statement_service import (
    fetch_financial_statements_from_dart,
)
from database.financial_statement_repository import (
    save_financial_statements,
)


class BatchPrepareFinancialDataError(Exception):
    """
    여러 기업의 재무 분석 데이터 준비 과정에서 발생하는 오류.
    """


def prepare_multiple_financial_data(
    corporations: list[dict[str, Any]],
    bsns_year: str,
    reprt_code: str = "11011",
    fs_div: str = "CFS",
    max_workers: int = 3,
    request_interval: float = 0.4,
) -> dict[str, Any]:
    """
    여러 기업의 재무 분석 데이터를 일괄 준비한다.

    처리 방식
    ----------
    1. 기업별 DART 재무제표 조회는 ThreadPoolExecutor로 병렬 수행한다.
    2. API 요청이 한꺼번에 시작되지 않도록 작업 제출 사이에
       request_interval만큼 간격을 둔다.
    3. SQLite 충돌을 피하기 위해 재무제표 저장과
       재무비율·증감률 계산 및 저장은 메인 스레드에서 순차 수행한다.
    4. 특정 기업이 실패해도 나머지 기업 처리는 계속한다.
    """
    _validate_batch_conditions(
        corporations=corporations,
        bsns_year=bsns_year,
        reprt_code=reprt_code,
        fs_div=fs_div,
        max_workers=max_workers,
        request_interval=request_interval,
    )

    unique_corporations = _deduplicate_corporations(
        corporations
    )

    fetch_successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    future_map: dict[
        Future[list[dict[str, Any]]],
        dict[str, Any],
    ] = {}

    with ThreadPoolExecutor(
        max_workers=max_workers,
    ) as executor:
        for index, corporation in enumerate(
            unique_corporations
        ):
            future = executor.submit(
                fetch_financial_statements_from_dart,
                corp_code=corporation["corp_code"],
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )

            future_map[future] = corporation

            if (
                request_interval > 0
                and index < len(unique_corporations) - 1
            ):
                sleep(request_interval)

        for future in as_completed(future_map):
            corporation = future_map[future]

            try:
                statements = future.result()

            except Exception as error:
                failures.append(
                    _build_failure_result(
                        corporation=corporation,
                        stage="financial_statements_fetch",
                        error=error,
                    )
                )
                continue

            fetch_successes.append(
                {
                    "corporation": corporation,
                    "statements": statements,
                }
            )

    successes: list[dict[str, Any]] = []

    # 입력 순서를 유지하기 위해 corp_code 기준으로 다시 정렬한다.
    fetch_result_by_code = {
        item["corporation"]["corp_code"]: item
        for item in fetch_successes
    }

    for corporation in unique_corporations:
        corp_code = corporation["corp_code"]
        fetched = fetch_result_by_code.get(corp_code)

        if fetched is None:
            continue

        statements = fetched["statements"]

        try:
            saved_statement_count = (
                save_financial_statements(statements)
            )

        except Exception as error:
            failures.append(
                _build_failure_result(
                    corporation=corporation,
                    stage="financial_statements_save",
                    error=error,
                )
            )
            continue

        try:
            ratio_result = (
                calculate_and_save_financial_ratios(
                    corp_code=corp_code,
                    bsns_year=bsns_year,
                    reprt_code=reprt_code,
                    fs_div=fs_div,
                )
            )

        except Exception as error:
            failures.append(
                _build_failure_result(
                    corporation=corporation,
                    stage="financial_ratios",
                    error=error,
                )
            )
            continue

        try:
            change_results = (
                calculate_and_save_account_change_ratios(
                    corp_code=corp_code,
                    bsns_year=bsns_year,
                    reprt_code=reprt_code,
                    fs_div=fs_div,
                )
            )

        except Exception as error:
            failures.append(
                _build_failure_result(
                    corporation=corporation,
                    stage="account_changes",
                    error=error,
                )
            )
            continue

        successes.append(
            {
                "corp_code": corp_code,
                "corp_name": corporation["corp_name"],
                "received_statement_count": len(statements),
                "saved_statement_count": (
                    saved_statement_count
                ),
                "ignored_statement_count": (
                    len(statements)
                    - saved_statement_count
                ),
                "calculated_ratio_count": ratio_result[
                    "calculated_count"
                ],
                "saved_ratio_count": ratio_result[
                    "saved_count"
                ],
                "calculated_change_count": len(
                    change_results
                ),
            }
        )

    return {
        "bsns_year": bsns_year,
        "reprt_code": reprt_code,
        "fs_div": fs_div,
        "requested_count": len(corporations),
        "unique_count": len(unique_corporations),
        "success_count": len(successes),
        "failure_count": len(failures),
        "successes": successes,
        "failures": failures,
    }


def _deduplicate_corporations(
    corporations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    corp_code 기준으로 중복 기업을 제거하며 입력 순서를 유지한다.
    """
    unique: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    for corporation in corporations:
        corp_code = str(
            corporation.get("corp_code") or ""
        ).strip()

        if not corp_code or corp_code in seen_codes:
            continue

        seen_codes.add(corp_code)
        unique.append(corporation)

    return unique


def _build_failure_result(
    corporation: dict[str, Any],
    stage: str,
    error: Exception,
) -> dict[str, Any]:
    return {
        "corp_code": corporation.get("corp_code"),
        "corp_name": corporation.get("corp_name"),
        "stage": stage,
        "error_type": type(error).__name__,
        "message": str(error),
    }


def _validate_batch_conditions(
    corporations: list[dict[str, Any]],
    bsns_year: str,
    reprt_code: str,
    fs_div: str,
    max_workers: int,
    request_interval: float,
) -> None:
    if not corporations:
        raise ValueError(
            "처리할 기업이 한 곳 이상 필요합니다."
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

    if max_workers <= 0:
        raise ValueError(
            "max_workers는 1 이상이어야 합니다."
        )

    if request_interval < 0:
        raise ValueError(
            "request_interval은 0 이상이어야 합니다."
        )