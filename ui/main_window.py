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

        self.financial_statement_tab = (
            FinancialStatementTab()
        )

        self.tabs.addTab(
            self.financial_statement_tab,
            "재무제표",
        )

        main_layout.addWidget(
            self.tabs
        )

        self.setCentralWidget(
            central_widget
        )

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