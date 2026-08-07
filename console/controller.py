from console.commands.corporation_commands import (
    initialize_corporations,
    handle_sync_corporations,
    handle_find_corporation,
)
from console.commands.financial_ratio_commands import (
    handle_account_change_ratios,
    handle_calculate_financial_ratios,
    handle_major_account_change_ratios,
    handle_show_financial_ratios,
)
from console.commands.financial_statement_commands import(
    handle_sync_financial_statements,
    handle_view_financial_statements,
)
from console.commands.tax_commands import(
    handle_calculate_effective_tax_rate,
    handle_tax_account_changes,
)
from console.commands.income_tax_note_commands import (
    handle_income_tax_note,
)
from console.commands.audit_commands import(
    handle_audit_report,
)
from console.corporation_selector import(
    select_corporation
)
from console.commands.eps_commands import handle_show_eps
from console.commands.prepare_commands import handle_prepare_financial_data
from console.commands.batch_prepare_commands import (
    handle_batch_prepare_financial_data,
)
from console.commands.compare_commands import (
    handle_compare_corporations,
)
from console.commands.industry_commands import (
    handle_industry_management,
)


class ConsoleController:
    """
    OpenDART Financial Analyzer의 콘솔 입력과
    서비스 호출 흐름을 관리한다.
    """

    def __init__(
        self,
        sync_corporations_on_start: bool = False,
    ) -> None:
        self.sync_corporations_on_start = (
            sync_corporations_on_start
        )

    def run(self) -> None:
        """
        콘솔 프로그램을 실행한다.
        """
        print("=" * 60)
        print("OpenDART Financial Analyzer")
        print("=" * 60)

        if self.sync_corporations_on_start:
            initialize_corporations()

        self._print_help()

        while True:
            command = input("\n선택> ").strip().lower()

            if command == "help":
                self._print_help()

            elif command == "sync":
                handle_sync_corporations()
            
            elif command == "find":
                handle_find_corporation()
            
            elif command == "fs":
                handle_sync_financial_statements()
            
            elif command == "view":
                handle_view_financial_statements()

            elif command == "ratio":
                handle_calculate_financial_ratios()
            
            elif command == "ratios":
                handle_show_financial_ratios()

            elif command == "change":
                handle_account_change_ratios()
            
            elif command == "major":
                handle_major_account_change_ratios()
            
            elif command == "etr":
                handle_calculate_effective_tax_rate()

            elif command == "tax-change":
                handle_tax_account_changes()

            elif command == "taxnote":
                handle_income_tax_note(select_corporation)

            elif command == "audit":
                handle_audit_report(select_corporation)

            elif command == "eps":
                handle_show_eps()

            elif command == "prepare":
                handle_prepare_financial_data()

            elif command == "batch-prepare":
                handle_batch_prepare_financial_data()

            elif command == "compare":
                handle_compare_corporations()

            elif command == "industry":
                handle_industry_management()
            
            elif command in {
                "exit",
                "quit",
            }:
                print("프로그램을 종료합니다.")
                break

            elif not command:
                continue

            else:
                print(
                    "알 수 없는 명령어입니다. "
                    "help를 입력하여 명령어를 확인하세요."
                )


    def _print_help(self) -> None:
        """
        사용 가능한 콘솔 명령어를 출력한다.
        """
        print(
            """
사용 가능한 명령어
------------------------------------------------------------
help                  명령어 목록 출력
sync                  DART 기업 고유번호 목록 동기화
find                  기업명 또는 종목코드로 기업 검색
fs                    기업 재무제표 수집 및 저장
view                  저장된 재무제표 출력
ratio                 저장된 재무제표로 재무비율 계산
ratios                저장된 재무비율 출력
change                계정별 당기·전기 금액과 증감률을 조회
major                 주요 계정 증감률 계산
etr                   실효세율 계산
tax-change            주요 세무관련 계정 증감 계산
taxnote               법인세비용 주석의 주요 구성항목을 조회
audit                 감사보고서 조회 및 주요 단락 분석
eps                   저장된 재무제표에서 기본·희석 EPS 조회
prepare               fs ratio change를 모두 실행하여 필요한 데이터를 저장
batch-prepare         여러 기업의 재무 데이터 일괄 준비
compare               여러 기업의 재무비율·증감률 비교
industry              산업군 생성 및 기업 목록 관리
exit                  프로그램 종료
"""
)

    
    
    

    

    


    