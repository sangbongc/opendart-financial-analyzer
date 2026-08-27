from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analysis.batch_prepare_service import (
    BatchPrepareFinancialDataError,
    prepare_multiple_financial_data,
)
from analysis.company_comparison_service import (
    CompanyComparisonError,
    RATIO_FORMATS,
    compare_corporation_financial_data,
)
from dart.corporation_service import (
    find_corporations_with_count,
)


class CompanyComparisonTab(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.conditions: dict[str, str] | None = None

        self.selected_corporations: dict[
            str,
            dict,
        ] = {}

        self.search_results: list[dict] = []

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 기업 검색
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "기업명 또는 종목코드"
        )

        self.search_button = QPushButton(
            "검색"
        )
        self.search_button.clicked.connect(
            self.search_corporations
        )

        self.search_input.returnPressed.connect(
            self.search_corporations
        )

        search_layout.addWidget(
            QLabel("비교 기업 검색")
        )
        search_layout.addWidget(
            self.search_input
        )
        search_layout.addWidget(
            self.search_button
        )

        layout.addLayout(
            search_layout
        )

        # 검색 결과
        self.search_result_list = QListWidget()

        self.search_result_list.itemDoubleClicked.connect(
            self.add_corporation
        )

        layout.addWidget(
            QLabel(
                "검색 결과 "
                "(더블클릭하여 비교 대상에 추가)"
            )
        )

        layout.addWidget(
            self.search_result_list
        )

        # 비교 대상
        target_layout = QHBoxLayout()

        self.selected_list = QListWidget()

        self.remove_button = QPushButton(
            "선택 기업 제거"
        )
        self.remove_button.clicked.connect(
            self.remove_corporation
        )

        target_layout.addWidget(
            self.selected_list
        )
        target_layout.addWidget(
            self.remove_button
        )

        layout.addWidget(
            QLabel("비교 대상")
        )

        layout.addLayout(
            target_layout
        )

        # 실행 버튼
        action_layout = QHBoxLayout()

        self.prepare_button = QPushButton(
            "비교 데이터 준비"
        )
        self.prepare_button.clicked.connect(
            self.prepare_comparison_data
        )

        self.compare_button = QPushButton(
            "비교 실행"
        )
        self.compare_button.clicked.connect(
            self.compare_corporations
        )

        action_layout.addStretch()

        action_layout.addWidget(
            self.prepare_button
        )

        action_layout.addWidget(
            self.compare_button
        )

        layout.addLayout(
            action_layout
        )

        self.info_label = QLabel(
            "비교할 기업을 추가한 후 "
            "데이터를 준비하거나 비교를 실행하세요."
        )

        layout.addWidget(
            self.info_label
        )

        # 결과
        self.table = QTableWidget()

        layout.addWidget(
            self.table
        )

    def set_context(
        self,
        conditions: dict[str, str],
    ) -> None:
        self.conditions = conditions

    def search_corporations(self) -> None:
        keyword = self.search_input.text().strip()

        if not keyword:
            QMessageBox.warning(
                self,
                "기업 검색",
                "검색어를 입력하세요.",
            )
            return

        try:
            result = find_corporations_with_count(
                keyword
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "기업 검색 오류",
                str(error),
            )
            return

        if isinstance(result, dict):
            corporations = (
                result.get("corporations")
                or result.get("rows")
                or result.get("results")
                or []
            )
        else:
            corporations = result

        self.search_results = list(
            corporations
        )

        self.search_result_list.clear()

        for index, corporation in enumerate(
            self.search_results
        ):
            corp_name = (
                corporation.get("corp_name")
                or "-"
            )

            stock_code = (
                corporation.get("stock_code")
                or "비상장"
            )

            item = QListWidgetItem(
                f"{corp_name} ({stock_code})"
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                index,
            )

            self.search_result_list.addItem(
                item
            )

    def add_corporation(
        self,
        item: QListWidgetItem,
    ) -> None:
        index = item.data(
            Qt.ItemDataRole.UserRole
        )

        corporation = self.search_results[
            index
        ]

        corp_code = str(
            corporation.get("corp_code")
            or ""
        )

        if not corp_code:
            return

        if corp_code in self.selected_corporations:
            return

        self.selected_corporations[
            corp_code
        ] = corporation

        self._refresh_selected_list()

    def remove_corporation(self) -> None:
        item = self.selected_list.currentItem()

        if item is None:
            return

        corp_code = item.data(
            Qt.ItemDataRole.UserRole
        )

        self.selected_corporations.pop(
            corp_code,
            None,
        )

        self._refresh_selected_list()

    def _refresh_selected_list(self) -> None:
        self.selected_list.clear()

        for corp_code, corporation in (
            self.selected_corporations.items()
        ):
            corp_name = (
                corporation.get("corp_name")
                or "-"
            )

            stock_code = (
                corporation.get("stock_code")
                or "비상장"
            )

            item = QListWidgetItem(
                f"{corp_name} ({stock_code})"
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                corp_code,
            )

            self.selected_list.addItem(
                item
            )

    def prepare_comparison_data(self) -> None:
        """
        선택된 기업들의 재무제표를 DART에서 수집하고,
        재무비율과 계정 증감률을 일괄 계산한다.
        """
        if self.conditions is None:
            QMessageBox.warning(
                self,
                "비교 데이터 준비",
                "조회조건을 확인할 수 없습니다.",
            )
            return

        corporations = list(
            self.selected_corporations.values()
        )

        if not corporations:
            QMessageBox.warning(
                self,
                "비교 데이터 준비",
                "데이터를 준비할 기업을 "
                "한 곳 이상 추가하세요.",
            )
            return

        try:
            result = prepare_multiple_financial_data(
                corporations=corporations,
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

        except (
            BatchPrepareFinancialDataError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "비교 데이터 준비",
                str(error),
            )
            return

        except Exception as error:
            QMessageBox.critical(
                self,
                "비교 데이터 준비 오류",
                str(error),
            )
            return

        self._show_prepare_result(
            result
        )

    def _show_prepare_result(
        self,
        result: dict,
    ) -> None:
        success_count = result[
            "success_count"
        ]

        failure_count = result[
            "failure_count"
        ]

        message_parts = [
            (
                f"요청 기업: "
                f"{result['requested_count']:,}개"
            ),
            (
                f"중복 제거 후: "
                f"{result['unique_count']:,}개"
            ),
            (
                f"성공: "
                f"{success_count:,}개"
            ),
            (
                f"실패: "
                f"{failure_count:,}개"
            ),
        ]

        failures = result.get(
            "failures",
            [],
        )

        if failures:
            message_parts.append(
                "\n[실패 기업]"
            )

            for failure in failures:
                corp_name = (
                    failure.get("corp_name")
                    or failure.get("corp_code")
                    or "-"
                )

                stage = (
                    failure.get("stage")
                    or "-"
                )

                error_message = (
                    failure.get("message")
                    or "-"
                )

                message_parts.append(
                    f"- {corp_name} "
                    f"/ {stage}\n"
                    f"  {error_message}"
                )

        QMessageBox.information(
            self,
            "비교 데이터 준비 완료",
            "\n".join(
                message_parts
            ),
        )

        self.info_label.setText(
            (
                f"{result['bsns_year']} "
                f"/ {result['reprt_code']} "
                f"/ {result['fs_div']} "
                f"/ 데이터 준비 "
                f"{success_count}개 성공, "
                f"{failure_count}개 실패"
            )
        )

    def compare_corporations(self) -> None:
        if self.conditions is None:
            QMessageBox.warning(
                self,
                "기업 비교",
                "조회조건을 확인할 수 없습니다.",
            )
            return

        corporations = list(
            self.selected_corporations.values()
        )

        if len(corporations) < 2:
            QMessageBox.warning(
                self,
                "기업 비교",
                "비교할 기업을 2개 이상 추가하세요.",
            )
            return

        try:
            result = (
                compare_corporation_financial_data(
                    corporations=corporations,
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

        except (
            CompanyComparisonError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "기업 비교",
                str(error),
            )
            return

        except Exception as error:
            QMessageBox.critical(
                self,
                "기업 비교 오류",
                str(error),
            )
            return

        self._populate_table(
            result
        )

        self.info_label.setText(
            f"{result['bsns_year']} "
            f"/ {result['reprt_code']} "
            f"/ {result['fs_div']} "
            f"/ 비교기업 "
            f"{result['corporation_count']}개"
        )

        missing = result[
            "missing_corporations"
        ]

        if missing:
            QMessageBox.information(
                self,
                "비교 데이터 확인",
                (
                    "저장된 비교 데이터가 없는 기업:\n"
                    + ", ".join(missing)
                    + "\n\n"
                    "비교 데이터 준비를 실행하면 "
                    "필요한 데이터를 일괄 준비할 수 있습니다."
                ),
            )

    def _populate_table(
        self,
        result: dict,
    ) -> None:
        columns = result[
            "columns"
        ]

        rows = result[
            "rows"
        ]

        self.table.clear()

        self.table.setColumnCount(
            len(columns) + 1
        )

        self.table.setHorizontalHeaderLabels(
            [
                "기업명",
                *[
                    column_name
                    for _, column_name in columns
                ],
            ]
        )

        self.table.setRowCount(
            len(rows)
        )

        for row_index, row in enumerate(
            rows
        ):
            company_item = QTableWidgetItem(
                str(row["corp_name"])
            )

            self.table.setItem(
                row_index,
                0,
                company_item,
            )

            for column_index, (
                column_code,
                _,
            ) in enumerate(
                columns,
                start=1,
            ):
                value = row.get(
                    column_code
                )

                formatted_value = (
                    self._format_value(
                        column_code,
                        value,
                    )
                )

                item = QTableWidgetItem(
                    formatted_value
                )

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
    def _format_value(
        column_code: str,
        value: float | None,
    ) -> str:
        if value is None:
            return "-"

        format_type = RATIO_FORMATS.get(
            column_code
        )

        if format_type == "percentage":
            return f"{value:,.2f}%"

        if format_type == "turnover":
            return f"{value:,.2f}회"

        if format_type == "days":
            return f"{value:,.2f}일"

        if column_code.endswith(
            "_CHANGE"
        ):
            return f"{value:,.2f}%"

        return f"{value:,.2f}"