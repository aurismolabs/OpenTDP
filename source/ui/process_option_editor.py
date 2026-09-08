# ui/process_option_editor.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QComboBox
)
from models.manufacturing import ProcessOption


class ProcessOptionEditor(QDialog):
    def __init__(self, parent=None, existing: ProcessOption = None):
        super().__init__(parent)
        self.setWindowTitle("Process Option")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name = QLineEdit()

        self.revision = QLineEdit()
        self.revision.setPlaceholderText("e.g. A  /  1.0  /  2024-R2")

        self.description = QTextEdit()
        self.description.setFixedHeight(80)

        self.maturity = QComboBox()
        self.maturity.addItems([
            "Very Low — Ad hoc / Initial",
            "Low — Repeatable",
            "Moderate — Defined / Standardized",
            "High — Measured and Controlled",
            "Very High — Optimized",
        ])
        self.maturity.wheelEvent = lambda e: e.ignore()

        if existing:
            self.name.setText(existing.option_name)
            self.revision.setText(existing.revision)
            self.description.setPlainText(existing.description)
            self.maturity.setCurrentText(existing.maturity)

        form.addRow("Option Name:", self.name)
        form.addRow("Revision:", self.revision)
        form.addRow("Process Maturity:", self.maturity)
        form.addRow("Description:", self.description)
        layout.addLayout(form)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        layout.addWidget(btn_save)

    def get_data(self) -> dict:
        return {
            "OptionName": self.name.text().strip(),
            "Revision": self.revision.text().strip(),
            "Description": self.description.toPlainText().strip(),
            "Maturity": self.maturity.currentText(),
            "Steps": [],
        }
