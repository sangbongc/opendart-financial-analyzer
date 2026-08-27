from PySide6.QtCore import (
    Qt,
    Signal,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dart.corporation_service import (
    find_corporations_with_count,
)


class CorporationSearchWidget(QWidget):
    corporation_selected = Signal(dict)

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.selected_corporation: dict | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "기업명, 종목코드 또는 고유번호"
        )

        self.search_input.returnPressed.connect(
            self.search_corporations
        )

        self.search_button = QPushButton(
            "검색"
        )

        self.search_button.clicked.connect(
            self.search_corporations
        )

        search_layout.addWidget(
            self.search_input
        )

        search_layout.addWidget(
            self.search_button
        )

        main_layout.addLayout(
            search_layout
        )

        self.result_list = QListWidget()

        self.result_list.setMaximumHeight(
            180
        )

        self.result_list.itemClicked.connect(
            self.select_corporation
        )

        main_layout.addWidget(
            self.result_list
        )

        self.selected_label = QLabel(
            "선택된 기업: 없음"
        )

        main_layout.addWidget(
            self.selected_label
        )

    def search_corporations(
        self,
    ) -> None:
        keyword = (
            self.search_input
            .text()
            .strip()
        )

        if not keyword:
            QMessageBox.warning(
                self,
                "기업 검색",
                "검색어를 입력하세요.",
            )
            return

        try:
            result = (
                find_corporations_with_count(
                    keyword=keyword,
                    limit=20,
                )
            )

        except Exception as error:
            QMessageBox.critical(
                self,
                "기업 검색 오류",
                str(error),
            )
            return

        corporations = (
            result["corporations"]
        )

        self.result_list.clear()

        if not corporations:
            QMessageBox.information(
                self,
                "기업 검색",
                "검색 결과가 없습니다.",
            )
            return

        for corporation in corporations:
            stock_code = (
                corporation["stock_code"]
                or "비상장"
            )

            text = (
                f"{corporation['corp_name']} "
                f"/ {stock_code} "
                f"/ {corporation['corp_code']}"
            )

            item = QListWidgetItem(
                text
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                corporation,
            )

            self.result_list.addItem(
                item
            )

        if len(corporations) == 1:
            self._set_selected_corporation(
                corporations[0]
            )

    def select_corporation(
        self,
        item: QListWidgetItem,
    ) -> None:
        corporation = item.data(
            Qt.ItemDataRole.UserRole
        )

        self._set_selected_corporation(
            corporation
        )

    def _set_selected_corporation(
        self,
        corporation: dict,
    ) -> None:
        self.selected_corporation = corporation

        stock_code = (
            corporation["stock_code"]
            or "비상장"
        )

        self.selected_label.setText(
            "선택된 기업: "
            f"{corporation['corp_name']} "
            f"({stock_code})"
        )

        self.corporation_selected.emit(
            corporation
        )