from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QChart,
    QChartView,
    QLineSeries,
    QValueAxis,
)

from analysis.company_comparison_service import (
    BASE_RATIO_COLUMNS,
    CHANGE_COLUMNS,
    RATIO_FORMATS,
    WORKING_CAPITAL_COLUMNS,
)
from analysis.company_time_series_service import (
    CompanyTimeSeriesError,
    analyze_company_time_series,
)
from analysis.prepare_service import (
    PrepareFinancialDataError,
    prepare_financial_data,
)

class CompanyTimeSeriesTab(QWidget):
    def __init__(self) -> None:
        super().__init__()

        self.corporation: dict[str, Any] | None = None
        self.conditions: dict[str, Any] = {}
        self.current_result: dict[str, Any] | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        main_layout.addWidget(
            self._build_condition_widget()
        )

        self.result_tabs = QTabWidget()

        self.base_ratio_table = self._create_table(
            BASE_RATIO_COLUMNS
        )
        self.working_capital_table = self._create_table(
            WORKING_CAPITAL_COLUMNS
        )
        self.change_table = self._create_table(
            CHANGE_COLUMNS
        )

        self.result_tabs.addTab(
            self.base_ratio_table,
            "수익성·안정성",
        )
        self.result_tabs.addTab(
            self.working_capital_table,
            "운전자본",
        )
        self.result_tabs.addTab(
            self.change_table,
            "주요 계정 증감",
        )

        main_layout.addWidget(
            self.result_tabs
        )

        main_layout.addWidget(
            self._build_chart_widget()
        )

    def _build_condition_widget(
        self,
    ) -> QWidget:
        widget = QWidget()

        layout = QHBoxLayout(widget)

        self.company_label = QLabel(
            "선택된 기업이 없습니다."
        )

        layout.addWidget(
            self.company_label
        )

        layout.addStretch()

        form_layout = QFormLayout()

        self.start_year_spin = QSpinBox()
        self.start_year_spin.setRange(
            2000,
            2100,
        )
        self.start_year_spin.setValue(
            2023
        )

        self.end_year_spin = QSpinBox()
        self.end_year_spin.setRange(
            2000,
            2100,
        )
        self.end_year_spin.setValue(
            2025
        )

        form_layout.addRow(
            "시작연도",
            self.start_year_spin,
        )

        form_layout.addRow(
            "종료연도",
            self.end_year_spin,
        )

        layout.addLayout(
            form_layout
        )

        self.query_button = QPushButton(
            "조회"
        )
        self.query_button.clicked.connect(
            self._load_time_series
        )

        layout.addWidget(
            self.query_button
        )

        self.prepare_button = QPushButton(
            "누락 자료 준비"
        )
        self.prepare_button.clicked.connect(
            self._prepare_missing_years
        )

        layout.addWidget(
            self.prepare_button
        )

        return widget

    def _build_chart_widget(
        self,
    ) -> QWidget:
        widget = QWidget()

        layout = QVBoxLayout(widget)

        top_layout = QHBoxLayout()

        title_label = QLabel(
            "지표 시각화"
        )

        top_layout.addWidget(
            title_label
        )

        top_layout.addStretch()

        self.metric_combo = QComboBox()

        self._populate_metric_combo()

        self.metric_combo.currentIndexChanged.connect(
            self._update_chart
        )

        top_layout.addWidget(
            QLabel("지표")
        )
        top_layout.addWidget(
            self.metric_combo
        )

        layout.addLayout(
            top_layout
        )

        self.chart = QChart()

        self.chart.setTitle(
            "조회 후 지표를 선택하세요."
        )

        self.chart_view = QChartView(
            self.chart
        )

        self.chart_view.setMinimumHeight(
            300
        )

        layout.addWidget(
            self.chart_view
        )

        return widget

    def _populate_metric_combo(
        self,
    ) -> None:
        self.metric_combo.clear()

        for code, name in (
            *BASE_RATIO_COLUMNS,
            *WORKING_CAPITAL_COLUMNS,
            *CHANGE_COLUMNS,
        ):
            self.metric_combo.addItem(
                name,
                code,
            )

    def _create_table(
        self,
        columns: tuple[
            tuple[str, str],
            ...,
        ],
    ) -> QTableWidget:
        table = QTableWidget()

        table.setColumnCount(
            1 + len(columns)
        )

        headers = [
            "연도",
            *[
                name
                for _, name in columns
            ],
        ]

        table.setHorizontalHeaderLabels(
            headers
        )

        table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectItems
        )

        table.setAlternatingRowColors(
            True
        )

        table.horizontalHeader().setStretchLastSection(
            True
        )

        return table

    def set_context(
        self,
        corporation: dict[str, Any] | None,
        conditions: dict[str, Any] | None = None,
    ) -> None:
        self.corporation = corporation
        self.conditions = conditions or {}

        if corporation is None:
            self.company_label.setText(
                "선택된 기업이 없습니다."
            )
            return

        corp_name = str(
            corporation.get("corp_name")
            or ""
        )

        stock_code = str(
            corporation.get("stock_code")
            or ""
        )

        if stock_code:
            text = (
                f"{corp_name} "
                f"({stock_code})"
            )
        else:
            text = corp_name

        self.company_label.setText(
            text
        )

    def _load_time_series(
        self,
    ) -> None:
        if self.corporation is None:
            QMessageBox.warning(
                self,
                "기업 선택 필요",
                "먼저 기업을 선택하세요.",
            )
            return

        start_year = str(
            self.start_year_spin.value()
        )
        end_year = str(
            self.end_year_spin.value()
        )

        if int(start_year) > int(end_year):
            QMessageBox.warning(
                self,
                "조회 조건 오류",
                "시작연도는 종료연도보다 "
                "클 수 없습니다.",
            )
            return

        reprt_code = str(
            self.conditions.get(
                "reprt_code",
                "11011",
            )
        )

        fs_div = str(
            self.conditions.get(
                "fs_div",
                "CFS",
            )
        )

        try:
            result = analyze_company_time_series(
                corporation=self.corporation,
                start_year=start_year,
                end_year=end_year,
                reprt_code=reprt_code,
                fs_div=fs_div,
            )

        except (
            CompanyTimeSeriesError,
            ValueError,
        ) as error:
            QMessageBox.warning(
                self,
                "시계열 조회 실패",
                str(error),
            )
            return

        except Exception as error:
            QMessageBox.critical(
                self,
                "오류",
                (
                    "기업 시계열 분석 중 "
                    "예상하지 못한 오류가 "
                    "발생했습니다.\n\n"
                    f"{error}"
                ),
            )
            return

        self.current_result = result

        self._refresh_result_widgets(
            result
        )

    def _fill_table(
        self,
        table: QTableWidget,
        columns: tuple[
            tuple[str, str],
            ...,
        ],
        rows: list[dict[str, Any]],
    ) -> None:
        table.setRowCount(
            len(rows)
        )

        for row_index, row in enumerate(
            rows
        ):
            year_item = QTableWidgetItem(
                str(
                    row.get(
                        "bsns_year",
                        "",
                    )
                )
            )

            year_item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            table.setItem(
                row_index,
                0,
                year_item,
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

                text = self._format_value(
                    column_code=column_code,
                    value=value,
                )

                item = QTableWidgetItem(
                    text
                )

                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignRight
                    | Qt.AlignmentFlag.AlignVCenter
                )

                table.setItem(
                    row_index,
                    column_index,
                    item,
                )

        table.resizeColumnsToContents()

    def _refresh_result_widgets(
        self,
        result: dict[str, Any],
    ) -> None:
        self._fill_table(
            table=self.base_ratio_table,
            columns=BASE_RATIO_COLUMNS,
            rows=result["rows"],
        )

        self._fill_table(
            table=self.working_capital_table,
            columns=WORKING_CAPITAL_COLUMNS,
            rows=result["rows"],
        )

        self._fill_table(
            table=self.change_table,
            columns=CHANGE_COLUMNS,
            rows=result["rows"],
        )

        self._update_chart()

    def _format_value(
        self,
        column_code: str,
        value: Any,
    ) -> str:
        if value is None:
            return "-"

        format_type = RATIO_FORMATS.get(
            column_code
        )

        numeric_value = float(value)

        if format_type == "turnover":
            return (
                f"{numeric_value:.2f}회"
            )

        if format_type == "days":
            return (
                f"{numeric_value:.2f}일"
            )

        return (
            f"{numeric_value:.2f}%"
        )

    def _update_chart(
        self,
    ) -> None:
        self.chart.removeAllSeries()

        for axis in list(
            self.chart.axes()
        ):
            self.chart.removeAxis(
                axis
            )

        if self.current_result is None:
            self.chart.setTitle(
                "조회 후 지표를 선택하세요."
            )
            return

        metric_code = (
            self.metric_combo.currentData()
        )

        metric_name = (
            self.metric_combo.currentText()
        )

        if not metric_code:
            return

        series = QLineSeries()
        series.setName(
            metric_name
        )

        years: list[str] = []
        values: list[float] = []

        point_index = 0

        for row in self.current_result[
            "rows"
        ]:
            value = row.get(
                metric_code
            )

            if value is None:
                continue

            years.append(
                str(
                    row["bsns_year"]
                )
            )

            numeric_value = float(
                value
            )

            values.append(
                numeric_value
            )

            series.append(
                point_index,
                numeric_value,
            )

            point_index += 1

        self.chart.addSeries(
            series
        )

        self.chart.setTitle(
            metric_name
        )

        if not values:
            return

        axis_x = QBarCategoryAxis()
        axis_x.append(
            years
        )

        self.chart.addAxis(
            axis_x,
            Qt.AlignmentFlag.AlignBottom,
        )

        series.attachAxis(
            axis_x
        )

        axis_y = QValueAxis()

        minimum = min(
            values
        )
        maximum = max(
            values
        )

        if minimum == maximum:
            margin = (
                abs(minimum) * 0.1
                if minimum != 0
                else 1.0
            )
        else:
            margin = (
                maximum - minimum
            ) * 0.1

        axis_y.setRange(
            minimum - margin,
            maximum + margin,
        )

        format_type = RATIO_FORMATS.get(
            metric_code,
            "percentage",
        )

        if format_type == "turnover":
            axis_y.setTitleText(
                "회"
            )

        elif format_type == "days":
            axis_y.setTitleText(
                "일"
            )

        else:
            axis_y.setTitleText(
                "%"
            )

        axis_y.setLabelFormat(
            "%.2f"
        )

        self.chart.addAxis(
            axis_y,
            Qt.AlignmentFlag.AlignLeft,
        )

        series.attachAxis(
            axis_y
        )

        self.chart.legend().setVisible(
            False
        )

    def _prepare_missing_years(
        self,
    ) -> None:
        if self.corporation is None:
            QMessageBox.warning(
                self,
                "기업 선택 필요",
                "먼저 기업을 선택하세요.",
            )
            return

        start_year = str(
            self.start_year_spin.value()
        )
        end_year = str(
            self.end_year_spin.value()
        )

        if int(start_year) > int(end_year):
            QMessageBox.warning(
                self,
                "조회 조건 오류",
                "시작연도는 종료연도보다 "
                "클 수 없습니다.",
            )
            return

        reprt_code = str(
            self.conditions.get(
                "reprt_code",
                "11011",
            )
        )

        fs_div = str(
            self.conditions.get(
                "fs_div",
                "CFS",
            )
        )

        #
        # 현재 DB 상태를 먼저 조회해서
        # 실제로 비어 있는 연도만 찾는다.
        #
        try:
            current_result = (
                analyze_company_time_series(
                    corporation=self.corporation,
                    start_year=start_year,
                    end_year=end_year,
                    reprt_code=reprt_code,
                    fs_div=fs_div,
                )
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "누락 자료 확인 실패",
                (
                    "현재 저장된 시계열 자료를 "
                    "확인하지 못했습니다.\n\n"
                    f"{error}"
                ),
            )
            return

        missing_years = current_result.get(
            "missing_years",
            [],
        )

        if not missing_years:
            QMessageBox.information(
                self,
                "자료 확인",
                (
                    f"{start_year}~{end_year} 사업연도의 "
                    "시계열 분석 자료가 모두 준비되어 있습니다."
                ),
            )

            self.current_result = current_result

            self._refresh_result_widgets(
                current_result
            )
            return

        corp_name = str(
            self.corporation.get(
                "corp_name"
            )
            or self.corporation.get(
                "corp_code"
            )
        )

        answer = QMessageBox.question(
            self,
            "누락 자료 준비",
            (
                f"{corp_name}의 다음 사업연도 자료가 "
                "비어 있습니다.\n\n"
                f"{', '.join(missing_years)}\n\n"
                "DART에서 재무제표를 수집하고 "
                "재무비율 및 계정 증감률을 계산하시겠습니까?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        corp_code = str(
            self.corporation["corp_code"]
        )

        successes: list[str] = []
        failures: list[
            tuple[str, str]
        ] = []

        self.prepare_button.setEnabled(
            False
        )
        self.query_button.setEnabled(
            False
        )

        QApplication.setOverrideCursor(
            Qt.CursorShape.WaitCursor
        )

        try:
            for year in missing_years:
                try:
                    prepare_financial_data(
                        corp_code=corp_code,
                        bsns_year=year,
                        reprt_code=reprt_code,
                        fs_div=fs_div,
                    )

                except PrepareFinancialDataError as error:
                    failures.append(
                        (
                            year,
                            str(error),
                        )
                    )
                    continue

                except Exception as error:
                    failures.append(
                        (
                            year,
                            str(error),
                        )
                    )
                    continue

                successes.append(
                    year
                )

        finally:
            QApplication.restoreOverrideCursor()

            self.prepare_button.setEnabled(
                True
            )
            self.query_button.setEnabled(
                True
            )

        #
        # prepare가 끝난 뒤 DB를 다시 조회해서
        # 표와 그래프를 즉시 갱신한다.
        #
        try:
            refreshed_result = (
                analyze_company_time_series(
                    corporation=self.corporation,
                    start_year=start_year,
                    end_year=end_year,
                    reprt_code=reprt_code,
                    fs_div=fs_div,
                )
            )

            self.current_result = (
                refreshed_result
            )

            self._refresh_result_widgets(
                refreshed_result
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "재조회 실패",
                (
                    "자료 준비는 완료되었지만 "
                    "화면을 다시 조회하지 못했습니다.\n\n"
                    f"{error}"
                ),
            )

        message_parts: list[str] = []

        if successes:
            message_parts.append(
                "준비 완료: "
                + ", ".join(successes)
            )

        if failures:
            failure_text = "\n".join(
                f"- {year}: {message}"
                for year, message in failures
            )

            message_parts.append(
                "준비 실패:\n"
                + failure_text
            )

        if failures:
            QMessageBox.warning(
                self,
                "누락 자료 준비 결과",
                "\n\n".join(
                    message_parts
                ),
            )

        else:
            QMessageBox.information(
                self,
                "누락 자료 준비 완료",
                "\n\n".join(
                    message_parts
                ),
            )