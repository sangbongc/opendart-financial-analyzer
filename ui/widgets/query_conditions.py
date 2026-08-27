from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QSpinBox,
    QWidget,
)

from utils import REPORT_CODE_NAMES


class QueryConditionsWidget(QWidget):
    conditions_changed = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)

        self.year_input = QSpinBox()
        self.year_input.setRange(
            2000,
            2100,
        )
        self.year_input.setValue(
            datetime.now().year - 1
        )

        self.year_input.valueChanged.connect(
            lambda _value: self.conditions_changed.emit()
        )

        layout.addRow(
            "사업연도",
            self.year_input,
        )

        self.report_combo = QComboBox()

        for code, name in REPORT_CODE_NAMES.items():
            self.report_combo.addItem(
                name,
                code,
            )

        self.report_combo.currentIndexChanged.connect(
            lambda _index: self.conditions_changed.emit()
        )
        layout.addRow(
            "보고서",
            self.report_combo,
        )

        self.fs_div_combo = QComboBox()

        self.fs_div_combo.addItem(
            "연결재무제표",
            "CFS",
        )

        self.fs_div_combo.addItem(
            "별도재무제표",
            "OFS",
        )

        self.fs_div_combo.currentIndexChanged.connect(
            lambda _index: self.conditions_changed.emit()
        )

        layout.addRow(
            "재무제표",
            self.fs_div_combo,
        )

    def get_conditions(
        self,
    ) -> dict[str, str]:
        return {
            "bsns_year": str(
                self.year_input.value()
            ),
            "reprt_code": str(
                self.report_combo.currentData()
            ),
            "fs_div": str(
                self.fs_div_combo.currentData()
            ),
        }