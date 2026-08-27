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

from database.financial_statement_repository import (
    fetch_financial_statements_from_db,
)
from dart.financial_statement_service import (
    sync_financial_statements,
)
from utils import format_amount


class FinancialStatementTab(QWidget):
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

        # 재무제표 종류
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

        # DB 조회 버튼
        self.query_button = QPushButton(
            "DB 조회"
        )

        self.query_button.clicked.connect(
            self.load_financial_statements
        )

        # DART 수집 버튼
        self.sync_button = QPushButton(
            "DART 수집/갱신"
        )

        self.sync_button.clicked.connect(
            self.sync_from_dart
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
            self.sync_button
        )

        layout.addLayout(
            control_layout
        )

        # 현재 조회정보
        self.info_label = QLabel(
            "기업과 조회조건을 선택한 후 "
            "DB 조회를 실행하세요."
        )

        layout.addWidget(
            self.info_label
        )

        # 재무제표 테이블
        self.table = QTableWidget()

        self.table.setColumnCount(4)

        self.table.setHorizontalHeaderLabels(
            [
                "계정명",
                "당기 금액",
                "전기 금액",
                "계정코드",
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

    def load_financial_statements(
        self,
    ) -> None:
        if self.corporation is None:
            QMessageBox.warning(
                self,
                "재무제표 조회",
                "먼저 기업을 선택하세요.",
            )
            return

        if self.conditions is None:
            QMessageBox.warning(
                self,
                "재무제표 조회",
                "조회조건을 확인할 수 없습니다.",
            )
            return

        sj_div = (
            self.statement_combo.currentData()
        )

        try:
            rows = fetch_financial_statements_from_db(
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
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "재무제표 조회 오류",
                str(error),
            )
            return

        if not rows:
            self.table.setRowCount(0)

            QMessageBox.information(
                self,
                "재무제표 조회",
                "해당 조건의 재무제표가 "
                "DB에 저장되어 있지 않습니다.",
            )
            return

        self._populate_table(
            rows
        )

        self.info_label.setText(
            f"{self.corporation['corp_name']} "
            f"/ {self.conditions['bsns_year']} "
            f"/ {self.conditions['reprt_code']} "
            f"/ {self.conditions['fs_div']} "
            f"/ {sj_div}"
        )

    def sync_from_dart(
        self,
    ) -> None:
        """
        현재 선택된 조건으로 DART에서 재무제표를
        수집하여 DB에 저장한 뒤 화면을 갱신한다.
        """
        if self.corporation is None:
            QMessageBox.warning(
                self,
                "DART 수집",
                "먼저 기업을 선택하세요.",
            )
            return

        if self.conditions is None:
            QMessageBox.warning(
                self,
                "DART 수집",
                "조회조건을 확인할 수 없습니다.",
            )
            return

        corp_code = self.corporation[
            "corp_code"
        ]

        bsns_year = self.conditions[
            "bsns_year"
        ]

        reprt_code = self.conditions[
            "reprt_code"
        ]

        fs_div = self.conditions[
            "fs_div"
        ]

        try:
            result = sync_financial_statements(
                corp_code=corp_code,
                bsns_year=bsns_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "DART 수집 오류",
                str(error),
            )
            return

        QMessageBox.information(
            self,
            "DART 수집 완료",
            (
                f"수신: "
                f"{result['received_count']:,}건\n"
                f"신규 저장: "
                f"{result['saved_count']:,}건\n"
                f"기존 데이터: "
                f"{result['ignored_count']:,}건"
            ),
        )

        # 수집한 데이터를 즉시 다시 조회한다.
        self.load_financial_statements()

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
                    row.get("thstrm_amount")
                ),
                format_amount(
                    row.get("frmtrm_amount")
                ),
                row.get("account_id") or "-",
            ]

            for column_index, value in enumerate(
                values
            ):
                self.table.setItem(
                    row_index,
                    column_index,
                    QTableWidgetItem(
                        str(value)
                    ),
                )

        self.table.resizeColumnsToContents()