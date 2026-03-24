# log_window.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal


class LogWindow(QWidget):
    closed = Signal()  # 👈 新增：窗口关闭时发出信号

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔊 语音监听日志")
        self.resize(500, 300)
        self.setWindowFlags(Qt.Window)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                font-family: Consolas, Courier, monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.text_edit)

        button_layout = QHBoxLayout()
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.clear_log)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)

    def append_log(self, message: str):
        self.text_edit.append(message)
        self.text_edit.verticalScrollBar().setValue(
            self.text_edit.verticalScrollBar().maximum()
        )

    def clear_log(self):
        self.text_edit.clear()

    def closeEvent(self, event):
        self.closed.emit()  # 👈 关键：关闭时通知主窗口
        event.accept()