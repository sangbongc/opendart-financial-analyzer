from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analysis.financial_ratio_service import (
    CALCULATION_VERSION,
    FinancialRatioCalculationError,
    calculate_and_save_financial_ratios,
)
from database.financial_ratio_repository import (
    fetch_financial_ratios,
)


RATIO_CATEGORIES = {
    "OPERATING_MARGIN": "수익성",
    "NET_PROFIT_MARGIN": "수익성",
    "ROA": "수익성",
    "ROE": "수익성",
    "DEBT_RATIO": "안정성",
    "CURRENT_RATIO": "안정성",
    "INVENTORY_TURNOVER": "효율성",
    "DIO": "효율성",
    "RECEIVABLE_TURNOVER": "효율성",
    "DSO": "효율성",
    "PAYABLE_TURNOVER": "효율성",
    "DPO": "효율성",
    "CCC": "효율성",
}


PERCENTAGE_RATIOS = {
    "OPERATING_MARGIN",
    "NET_PROFIT_MARGIN",
    "ROA",
    "ROE",
    "DEBT_RATIO",
    "CURRENT_RATIO",
}

TURNOVER_RATIOS = {
    "INVENTORY_TURNOVER",
    "RECEIVABLE_TURNOVER",
    "PAYABLE_TURNOVER",
}

DAY_RATIOS = {
    "DIO",
    "DSO",
    "DPO",
    "CCC",
}


class FinancialRatioTab(QWidget):
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

        self.query_button = QPushButton(
            "DB 조회"
        )
        self.query_button.clicked.connect(
            self.load_ratios
        )

        self.calculate_button = QPushButton(
            "계산/갱신"
        )
        self.calculate_button.clicked.connect(
            self.calculate_ratios
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
            "재무비율을 조회하세요."
        )

        layout.addWidget(
            self.info_label
        )

        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels(
            [
                "구분",
                "재무비율",
                "값",
                "계산 버전",
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

    def load_ratios(self) -> None:
        if not self._validate_context():
            return

        try:
            ratios = fetch_financial_ratios(
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
                    CALCULATION_VERSION
                ),
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "재무비율 조회 오류",
                str(error),
            )
            return

        if not ratios:
            self.table.setRowCount(0)

            QMessageBox.information(
                self,
                "재무비율 조회",
                "해당 조건으로 계산된 "
                "재무비율이 없습니다.",
            )
            return

        self._populate_table(
            ratios
        )

        self._update_info_label()

    def calculate_ratios(self) -> None:
        if not self._validate_context():
            return

        try:
            result = (
                calculate_and_save_financial_ratios(
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
                )
            )

        except FinancialRatioCalculationError as error:
            QMessageBox.warning(
                self,
                "재무비율 계산",
                str(error),
            )
            return

        except Exception as error:
            QMessageBox.critical(
                self,
                "재무비율 계산 오류",
                str(error),
            )
            return

        self._populate_table(
            result["ratios"]
        )

        self._update_info_label()

        unavailable = result[
            "unavailable_ratios"
        ]

        if unavailable:
            unavailable_text = ", ".join(
                unavailable
            )

            message = (
                f"{result['calculated_count']}개 "
                "재무비율을 계산했습니다.\n\n"
                "계산할 수 없는 비율:\n"
                f"{unavailable_text}"
            )

        else:
            message = (
                f"{result['calculated_count']}개 "
                "재무비율을 계산했습니다."
            )

        QMessageBox.information(
            self,
            "재무비율 계산 완료",
            message,
        )

    def _validate_context(self) -> bool:
        if self.corporation is None:
            QMessageBox.warning(
                self,
                "재무비율",
                "먼저 기업을 선택하세요.",
            )
            return False

        if self.conditions is None:
            QMessageBox.warning(
                self,
                "재무비율",
                "조회조건을 확인할 수 없습니다.",
            )
            return False

        return True

    def _update_info_label(self) -> None:
        self.info_label.setText(
            f"{self.corporation['corp_name']} "
            f"/ {self.conditions['bsns_year']} "
            f"/ {self.conditions['reprt_code']} "
            f"/ {self.conditions['fs_div']}"
        )

    def _populate_table(
        self,
        ratios: list[dict],
    ) -> None:
        self.table.setRowCount(
            len(ratios)
        )

        for row_index, ratio in enumerate(
            ratios
        ):
            ratio_code = ratio[
                "ratio_code"
            ]

            category = RATIO_CATEGORIES.get(
                ratio_code,
                "기타",
            )

            ratio_value = (
                self._format_ratio_value(
                    ratio_code=ratio_code,
                    value=ratio.get(
                        "ratio_value"
                    ),
                )
            )

            values = [
                category,
                ratio.get("ratio_name") or "-",
                ratio_value,
                ratio.get(
                    "calculation_version"
                ) or "-",
            ]

            for column_index, value in enumerate(
                values
            ):
                item = QTableWidgetItem(
                    str(value)
                )

                if column_index == 2:
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
    def _format_ratio_value(
        ratio_code: str,
        value: float | None,
    ) -> str:
        if value is None:
            return "계산 불가"

        if ratio_code in PERCENTAGE_RATIOS:
            return f"{value:,.2f}%"

        if ratio_code in TURNOVER_RATIOS:
            return f"{value:,.2f}회"

        if ratio_code in DAY_RATIOS:
            return f"{value:,.2f}일"

        return f"{value:,.2f}"