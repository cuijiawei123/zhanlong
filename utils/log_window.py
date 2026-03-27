# log_window.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, Signal


class LogWindow(QWidget):
    closed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔊 语音监听日志")
        self.resize(560, 360)
        self.setWindowFlags(Qt.Window)

        lay = QVBoxLayout()
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)
        self.setLayout(lay)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #11111b;
                color: #94e2d5;
                font-family: "Menlo", "Consolas", "Courier New", monospace;
                font-size: 12px;
                border: 1px solid #313244;
                border-radius: 8px;
                padding: 10px;
                selection-background-color: #cba6f7;
                selection-color: #1e1e2e;
            }
        """)
        lay.addWidget(self.text_edit)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("🗑  清空日志")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #313244; color: #cdd6f4;
                border: none; border-radius: 6px;
                padding: 8px 18px; font-size: 12px;
            }
            QPushButton:hover { background: #45475a; }
        """)
        clear_btn.clicked.connect(self.clear_log)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        lay.addLayout(btn_row)

    def append_log(self, msg: str):
        self.text_edit.append(msg)
        sb = self.text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def clear_log(self):
        self.text_edit.clear()

    def closeEvent(self, event):
        self.closed.emit()
        event.accept()
