import sys

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.corporation_search import (
    CorporationSearchWidget,
)
from ui.widgets.query_conditions import (
    QueryConditionsWidget,
)
from ui.tabs.financial_statement_tab import (
    FinancialStatementTab,
)
from ui.tabs.financial_ratio_tab import (
    FinancialRatioTab,
)
from ui.tabs.account_change_tab import (
    AccountChangeTab,
)
from ui.tabs.company_comparison_tab import (
    CompanyComparisonTab,
)
from ui.tabs.company_time_series_tab import (
    CompanyTimeSeriesTab,
)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()

        self.selected_corporation: dict | None = None

        self.setWindowTitle(
            "OpenDART Financial Analyzer"
        )

        self.resize(
            1200,
            800,
        )

        self._build_ui()

    def _build_ui(self) -> None:
        central_widget = QWidget()

        main_layout = QVBoxLayout(
            central_widget
        )

        title_label = QLabel(
            "OpenDART Financial Analyzer"
        )

        main_layout.addWidget(
            title_label
        )

        # 기업 검색
        self.corporation_search = (
            CorporationSearchWidget()
        )

        self.corporation_search.corporation_selected.connect(
            self._on_corporation_selected
        )

        main_layout.addWidget(
            self.corporation_search
        )

        # 조회 조건
        self.query_conditions = (
            QueryConditionsWidget()
        )

        self.query_conditions.conditions_changed.connect(
            self._update_tab_context
        )

        main_layout.addWidget(
            self.query_conditions
        )

        # 결과 탭
        self.tabs = QTabWidget()

        # 재무제표
        self.financial_statement_tab = (
            FinancialStatementTab()
        )

        self.tabs.addTab(
            self.financial_statement_tab,
            "재무제표",
        )

        # 재무비율
        self.financial_ratio_tab = (
            FinancialRatioTab()
        )

        self.tabs.addTab(
            self.financial_ratio_tab,
            "재무비율",
        )

        # 계정 증감분석
        self.account_change_tab = (
            AccountChangeTab()
        )

        self.tabs.addTab(
            self.account_change_tab,
            "계정 증감분석",
        )

        # 기업 비교
        self.company_comparison_tab = (
            CompanyComparisonTab()
        )

        self.tabs.addTab(
            self.company_comparison_tab,
            "기업 비교",
        )

        # 기업 시계열
        self.company_time_series_tab = (
            CompanyTimeSeriesTab()
        )

        self.tabs.addTab(
            self.company_time_series_tab,
            "기업 시계열",
        )

        main_layout.addWidget(
            self.tabs
        )

        self.setCentralWidget(
            central_widget
        )

        # 초기 조회조건을 모든 탭에 전달
        self._update_tab_context()

    def _on_corporation_selected(
        self,
        corporation: dict,
    ) -> None:
        """
        기업 검색 위젯에서 선택된 기업 정보를
        MainWindow에 보관하고 하위 탭에 전달한다.
        """
        self.selected_corporation = corporation

        corp_name = corporation["corp_name"]

        stock_code = (
            corporation["stock_code"]
            or "비상장"
        )

        self.statusBar().showMessage(
            f"선택된 기업: "
            f"{corp_name} ({stock_code})"
        )

        self._update_tab_context()

    def _update_tab_context(
        self,
    ) -> None:
        """
        현재 선택된 기업과 조회조건을
        하위 탭에 전달한다.
        """
        conditions = (
            self.query_conditions
            .get_conditions()
        )

        self.financial_statement_tab.set_context(
            corporation=self.selected_corporation,
            conditions=conditions,
        )

        self.financial_ratio_tab.set_context(
            corporation=self.selected_corporation,
            conditions=conditions,
        )

        self.account_change_tab.set_context(
            corporation=self.selected_corporation,
            conditions=conditions,
        )

        self.company_comparison_tab.set_context(
            conditions=conditions,
        )

        self.company_time_series_tab.set_context(
            corporation=self.selected_corporation,
            conditions=conditions,
        )


def run_ui() -> None:
    app = QApplication(
        sys.argv
    )

    window = MainWindow()
    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    run_ui()