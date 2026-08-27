from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analysis.account_change_ratio_service import (
    AccountChangeRatioError,
    calculate_and_save_account_change_ratios,
)
from database.financial_statement_change_repository import (
    DEFAULT_CALCULATION_VERSION,
    fetch_financial_statement_changes,
)
from utils import format_amount


class AccountChangeTab(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.corporation: dict | None = None
        self.conditions: dict[str, str] | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        control_layout = QHBoxLayout()

        self.statement_combo = QComboBox()

        self.statement_combo.addItem(
            "재무상태표",
            "BS",
        )
        self.statement_combo.addItem(
            "손익계산서",
            "IS",
        )
        self.statement_combo.addItem(
            "포괄손익계산서",
            "CIS",
        )
        self.statement_combo.addItem(
            "현금흐름표",
            "CF",
        )

        self.query_button = QPushButton(
            "DB 조회"
        )
        self.query_button.clicked.connect(
            self.load_changes
        )

        self.calculate_button = QPushButton(
            "계산/갱신"
        )
        self.calculate_button.clicked.connect(
            self.calculate_changes
        )

        control_layout.addWidget(
            QLabel("재무제표 종류")
        )
        control_layout.addWidget(
            self.statement_combo
        )

        control_layout.addStretch()

        control_layout.addWidget(
            self.query_button
        )
        control_layout.addWidget(
            self.calculate_button
        )

        layout.addLayout(
            control_layout
        )

        self.info_label = QLabel(
            "기업과 조회조건을 선택한 후 "
            "계정 증감분석을 조회하세요."
        )

        layout.addWidget(
            self.info_label
        )

        self.table = QTableWidget()

        self.table.setColumnCount(5)

        self.table.setHorizontalHeaderLabels(
            [
                "계정명",
                "당기 금액",
                "전기 금액",
                "증감액",
                "증감률",
            ]
        )

        layout.addWidget(
            self.table
        )

    def set_context(
        self,
        corporation: dict | None,
        conditions: dict[str, str],
    ) -> None:
        self.corporation = corporation
        self.conditions = conditions

    def load_changes(self) -> None:
        if not self._validate_context():
            return

        sj_div = (
            self.statement_combo.currentData()
        )

        try:
            rows = fetch_financial_statement_changes(
                corp_code=self.corporation[
                    "corp_code"
                ],
                bsns_year=self.conditions[
                    "bsns_year"
                ],
                reprt_code=self.conditions[
                    "reprt_code"
                ],
                fs_div=self.conditions[
                    "fs_div"
                ],
                sj_div=sj_div,
                calculation_version=(
                    DEFAULT_CALCULATION_VERSION
                ),
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "증감분석 조회 오류",
                str(error),
            )
            return

        if not rows:
            self.table.setRowCount(0)

            QMessageBox.information(
                self,
                "증감분석 조회",
                "해당 조건으로 저장된 "
                "증감분석 결과가 없습니다.",
            )
            return

        self._populate_table(
            rows
        )

        self._update_info_label(
            sj_div
        )

    def calculate_changes(self) -> None:
        if not self._validate_context():
            return

        try:
            results = (
                calculate_and_save_account_change_ratios(
                    corp_code=self.corporation[
                        "corp_code"
                    ],
                    bsns_year=self.conditions[
                        "bsns_year"
                    ],
                    reprt_code=self.conditions[
                        "reprt_code"
                    ],
                    fs_div=self.conditions[
                        "fs_div"
                    ],
                    calculation_version=(
                        DEFAULT_CALCULATION_VERSION
                    ),
                )
            )

        except AccountChangeRatioError as error:
            QMessageBox.warning(
                self,
                "증감분석 계산",
                str(error),
            )
            return

        except Exception as error:
            QMessageBox.critical(
                self,
                "증감분석 계산 오류",
                str(error),
            )
            return

        if not results:
            QMessageBox.information(
                self,
                "증감분석 계산",
                "계산할 재무제표 데이터가 없습니다.",
            )
            return

        QMessageBox.information(
            self,
            "증감분석 계산 완료",
            (
                f"{len(results):,}개 계정의 "
                "증감분석을 계산하고 저장했습니다."
            ),
        )

        self.load_changes()

    def _validate_context(self) -> bool:
        if self.corporation is None:
            QMessageBox.warning(
                self,
                "계정 증감분석",
                "먼저 기업을 선택하세요.",
            )
            return False

        if self.conditions is None:
            QMessageBox.warning(
                self,
                "계정 증감분석",
                "조회조건을 확인할 수 없습니다.",
            )
            return False

        return True

    def _update_info_label(
        self,
        sj_div: str,
    ) -> None:
        self.info_label.setText(
            f"{self.corporation['corp_name']} "
            f"/ {self.conditions['bsns_year']} "
            f"/ {self.conditions['reprt_code']} "
            f"/ {self.conditions['fs_div']} "
            f"/ {sj_div}"
        )

    def _populate_table(
        self,
        rows: list[dict],
    ) -> None:
        self.table.setRowCount(
            len(rows)
        )

        for row_index, row in enumerate(
            rows
        ):
            values = [
                row.get("account_nm") or "-",
                format_amount(
                    row.get("current_amount")
                ),
                format_amount(
                    row.get("previous_amount")
                ),
                format_amount(
                    row.get("change_amount")
                ),
                self._format_change_rate(
                    row.get("change_rate")
                ),
            ]

            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    str(value)
                )

                if column_index > 0:
                    item.setTextAlignment(
                        int(
                            Qt.AlignmentFlag.AlignRight
                            | Qt.AlignmentFlag.AlignVCenter
                        )
                    )

                self.table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        self.table.resizeColumnsToContents()

    @staticmethod
    def _format_change_rate(
        value: float | None,
    ) -> str:
        if value is None:
            return "계산 불가"

        return f"{value:,.2f}%"