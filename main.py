import sys
import os
import threading
import re
import pyautogui

from utils.config_manager import ConfigManager, get_resource_path
from utils.voice_engine import start_recording, stop_and_get_result
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox, QMainWindow,
    QScrollArea, QDialog, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QSize
from PySide6.QtGui import QFont, QPixmap, QColor, QCursor
from utils.voice_listener import VoiceListener
from utils.log_window import LogWindow


# ================= 配色常量 =================

C = {
    "bg":       "#1e1e2e",
    "surface":  "#181825",
    "card":     "#313244",
    "card_h":   "#45475a",
    "border":   "#45475a",
    "text":     "#cdd6f4",
    "subtext":  "#a6adc8",
    "dim":      "#6c7086",
    "purple":   "#cba6f7",
    "blue":     "#89b4fa",
    "teal":     "#94e2d5",
    "green":    "#a6e3a1",
    "yellow":   "#f9e2af",
    "pink":     "#f38ba8",
    "red":      "#f38ba8",
    "add_bg":   "#252536",
}

GLOBAL_STYLE = f"""
* {{ font-family: "PingFang SC", "Microsoft YaHei", "Segoe UI", sans-serif; }}
QWidget#MainBg {{ background: {C['bg']}; }}
QScrollArea {{ background: {C['bg']}; border: none; }}
QScrollArea > QWidget > QWidget {{ background: {C['bg']}; }}
QMessageBox {{ background: {C['bg']}; }}
QMessageBox QLabel {{ color: {C['text']}; font-size: 13px; }}
QMessageBox QPushButton {{
    background: {C['card']}; color: {C['text']};
    border: none; padding: 8px 24px; border-radius: 6px; font-size: 13px; min-width: 70px;
}}
QMessageBox QPushButton:hover {{ background: {C['card_h']}; }}
"""


# ================= 宏卡片 =================

class MacroCard(QWidget):
    edit_clicked = Signal(str)
    delete_clicked = Signal(str)

    def __init__(self, name, voice="", keys="", parent=None):
        super().__init__(parent)
        self.name = name
        self.setFixedSize(220, 140)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._build(name, voice, keys)

    def _build(self, name, voice, keys):
        self.setStyleSheet(f"""
            MacroCard {{
                background: {C['card']};
                border-radius: 12px;
                border: 1px solid transparent;
            }}
            MacroCard:hover {{
                border: 1px solid {C['purple']};
            }}
        """)

        lay = QVBoxLayout()
        lay.setContentsMargins(16, 14, 16, 10)
        lay.setSpacing(6)
        self.setLayout(lay)

        # 名称
        lbl_name = QLabel(name)
        lbl_name.setStyleSheet(f"color: {C['purple']}; font-size: 16px; font-weight: bold; background: transparent;")
        lay.addWidget(lbl_name)

        # 语音
        voice_display = voice if voice else "未设置语音"
        voice_color = C['teal'] if voice else C['dim']
        lbl_voice = QLabel(f"🎤  {voice_display}")
        lbl_voice.setStyleSheet(f"color: {voice_color}; font-size: 12px; background: transparent;")
        lbl_voice.setWordWrap(True)
        lay.addWidget(lbl_voice)

        # 按键
        keys_display = keys if keys else "未设置按键"
        keys_color = C['yellow'] if keys else C['dim']
        lbl_keys = QLabel(f"⌨️  {keys_display}")
        lbl_keys.setStyleSheet(f"color: {keys_color}; font-size: 12px; background: transparent;")
        lbl_keys.setWordWrap(True)
        lay.addWidget(lbl_keys)

        lay.addStretch()

        # 操作图标行
        icon_row = QHBoxLayout()
        icon_row.setSpacing(4)
        icon_row.addStretch()

        btn_edit = QPushButton("✏️")
        btn_edit.setToolTip("编辑")
        btn_edit.setFixedSize(30, 30)
        btn_edit.setCursor(Qt.PointingHandCursor)
        btn_edit.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; font-size: 16px; border-radius: 6px; }}
            QPushButton:hover {{ background: {C['card_h']}; }}
        """)
        btn_edit.clicked.connect(lambda: self.edit_clicked.emit(self.name))

        btn_del = QPushButton("🗑️")
        btn_del.setToolTip("删除")
        btn_del.setFixedSize(30, 30)
        btn_del.setCursor(Qt.PointingHandCursor)
        btn_del.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; font-size: 16px; border-radius: 6px; }}
            QPushButton:hover {{ background: #45273a; }}
        """)
        btn_del.clicked.connect(lambda: self.delete_clicked.emit(self.name))

        icon_row.addWidget(btn_edit)
        icon_row.addWidget(btn_del)
        lay.addLayout(icon_row)


# ================= 添加卡片（虚线框 +） =================

class AddCard(QWidget):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 140)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(f"""
            AddCard {{
                background: {C['add_bg']};
                border: 2px dashed {C['dim']};
                border-radius: 12px;
            }}
            AddCard:hover {{
                border-color: {C['purple']};
                background: {C['card']};
            }}
        """)

        lay = QVBoxLayout()
        lay.setAlignment(Qt.AlignCenter)
        self.setLayout(lay)

        lbl = QLabel("＋")
        lbl.setStyleSheet(f"color: {C['dim']}; font-size: 36px; font-weight: 300; background: transparent;")
        lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(lbl)

        txt = QLabel("添加新宏")
        txt.setStyleSheet(f"color: {C['dim']}; font-size: 13px; background: transparent;")
        txt.setAlignment(Qt.AlignCenter)
        lay.addWidget(txt)

    def mousePressEvent(self, event):
        self.clicked.emit()


# ================= 编辑/新建弹窗 =================

class EditDialog(QDialog):
    def __init__(self, parent=None, name="", voice="", keys="", is_new=True):
        super().__init__(parent)
        self.setWindowTitle("新建语音宏" if is_new else f"编辑 — {name}")
        self.setFixedSize(480, 340)
        self.setStyleSheet(f"""
            QDialog {{ background: {C['bg']}; }}
            QLabel {{ color: {C['text']}; font-size: 13px; background: transparent; }}
            QLineEdit {{
                background: {C['card']}; color: {C['text']};
                border: 1px solid {C['border']}; border-radius: 8px;
                padding: 10px 14px; font-size: 13px;
            }}
            QLineEdit:focus {{ border-color: {C['purple']}; }}
            QLineEdit::placeholder {{ color: {C['dim']}; }}
        """)

        self.is_new = is_new
        self._is_recording = False

        lay = QVBoxLayout()
        lay.setSpacing(14)
        lay.setContentsMargins(28, 24, 28, 20)
        self.setLayout(lay)

        # 名称
        lay.addWidget(self._lbl("操作命名"))
        self.input_name = QLineEdit(name)
        self.input_name.setPlaceholderText("随意命名，方便记忆")
        if not is_new:
            self.input_name.setReadOnly(True)
            self.input_name.setStyleSheet(self.input_name.styleSheet() + f"color: {C['dim']};")
        lay.addWidget(self.input_name)

        # 按键
        lay.addWidget(self._lbl("录入按键"))
        self.input_keys = QLineEdit(keys)
        self.input_keys.setPlaceholderText("空格隔开  例: a b c    组合键: (ctrl,c)")
        lay.addWidget(self.input_keys)

        # 语音
        lay.addWidget(self._lbl("录入语音"))
        voice_row = QHBoxLayout()
        self.input_voice = QLineEdit(voice)
        self.input_voice.setPlaceholderText("长按话筒录入")
        voice_row.addWidget(self.input_voice)

        self.btn_mic = QPushButton("🎤")
        self.btn_mic.setFixedSize(42, 42)
        self.btn_mic.setCursor(Qt.PointingHandCursor)
        self.btn_mic.setStyleSheet(f"""
            QPushButton {{
                background: {C['card']}; border: 1.5px solid {C['border']};
                border-radius: 21px; font-size: 18px;
            }}
            QPushButton:hover {{ border-color: {C['purple']}; }}
            QPushButton:pressed {{ background: {C['pink']}; border-color: {C['pink']}; }}
        """)
        self.btn_mic.pressed.connect(self._mic_pressed)
        self.btn_mic.released.connect(self._mic_released)
        voice_row.addWidget(self.btn_mic)
        lay.addLayout(voice_row)

        lay.addStretch()

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_cancel = QPushButton("取消")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"""
            QPushButton {{
                background: {C['card']}; color: {C['text']};
                border: none; border-radius: 8px; padding: 10px 0; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {C['card_h']}; }}
        """)
        btn_cancel.clicked.connect(self.reject)

        btn_ok = QPushButton("保存" if not is_new else "添加")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.setStyleSheet(f"""
            QPushButton {{
                background: {C['green']}; color: {C['bg']};
                border: none; border-radius: 8px; padding: 10px 0; font-size: 13px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {C['teal']}; }}
        """)
        btn_ok.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        lay.addLayout(btn_row)

    @staticmethod
    def _lbl(text):
        l = QLabel(text)
        l.setStyleSheet(f"color: {C['blue']}; font-weight: bold; font-size: 12px; background: transparent;")
        return l

    def _mic_pressed(self):
        if self._is_recording:
            return
        if not start_recording():
            return
        self._is_recording = True
        self.input_voice.setText("🎤 录音中...")
        self.input_voice.setStyleSheet(f"color: {C['pink']}; font-weight: bold;")

    def _mic_released(self):
        if not self._is_recording:
            return
        self.input_voice.setText("⏳ 识别中...")
        QApplication.processEvents()
        raw, pinyin = stop_and_get_result()
        if raw == "错误":
            self.input_voice.setText(f"❌ {pinyin}")
        elif not raw:
            self.input_voice.setText("")
        else:
            self.input_voice.setText(pinyin)
            self.input_voice.setStyleSheet(f"color: {C['green']}; font-weight: bold;")
        self._is_recording = False

    def get_data(self):
        return (
            self.input_name.text().strip(),
            self.input_voice.text().strip(),
            self.input_keys.text().strip()
        )


# ================= 主窗口 =================

class MacroTrainerUI(QWidget):
    log_signal = Signal(str)
    status_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("MainBg")
        self.setWindowTitle("🐉 斩龙 · 语音宏配置器")
        self.resize(820, 620)
        self.setMinimumSize(600, 450)

        self.config = ConfigManager()
        self.config.load_config()

        self.listener = None
        self.log_window = None
        self.about_window = None

        self.log_signal.connect(self._handle_log)
        self.status_signal.connect(self._handle_status)

        QTimer.singleShot(100, self.show_about)

        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout()
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setLayout(root)

        # ── 顶栏 ──
        top_bar = QWidget()
        top_bar.setFixedHeight(60)
        top_bar.setStyleSheet(f"background: {C['surface']};")
        top_lay = QHBoxLayout()
        top_lay.setContentsMargins(24, 0, 24, 0)
        top_bar.setLayout(top_lay)

        title = QLabel("🐉  斩 龙")
        title.setStyleSheet(f"color: {C['purple']}; font-size: 20px; font-weight: bold; background: transparent;")
        top_lay.addWidget(title)

        top_lay.addStretch()

        self.listen_btn = QPushButton("🔊  开启监听")
        self.listen_btn.setCursor(Qt.PointingHandCursor)
        self.listen_btn.setFixedHeight(38)
        self.listen_btn.setStyleSheet(self._listen_idle_css())
        self.listen_btn.clicked.connect(self.toggle_listen)
        top_lay.addWidget(self.listen_btn)

        root.addWidget(top_bar)

        # ── 分隔线 ──
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['card']};")
        root.addWidget(sep)

        # ── 卡片滚动区 ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet(f"background: {C['bg']};")
        self.flow_layout = FlowLayout(self.cards_container, margin=24, spacing=16)

        scroll.setWidget(self.cards_container)
        root.addWidget(scroll, stretch=1)

        self._refresh_cards()

    # ── 监听按钮样式 ──

    @staticmethod
    def _listen_idle_css():
        return f"""
            QPushButton {{
                background: {C['blue']}; color: {C['bg']};
                font-weight: bold; font-size: 13px;
                padding: 0 24px; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: {C['purple']}; }}
        """

    @staticmethod
    def _listen_active_css():
        return f"""
            QPushButton {{
                background: {C['pink']}; color: {C['bg']};
                font-weight: bold; font-size: 13px;
                padding: 0 24px; border-radius: 8px; border: none;
            }}
            QPushButton:hover {{ background: #eba0ac; }}
        """

    # ── 刷新卡片 ──

    def _refresh_cards(self):
        # 清空
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        macros = self.config.get_macros_snapshot()
        keywords = self.config.get_keywords_snapshot()
        all_names = self.config.get_all_names()

        for name in all_names:
            voice = keywords.get(name, "")
            keys = self._actions_to_str(macros.get(name, []))
            card = MacroCard(name, voice, keys)
            card.edit_clicked.connect(self._on_edit)
            card.delete_clicked.connect(self._on_delete)
            self.flow_layout.addWidget(card)

        # 添加卡片
        add_card = AddCard()
        add_card.clicked.connect(self._on_add)
        self.flow_layout.addWidget(add_card)

    # ── 卡片操作 ──

    def _on_add(self):
        dlg = EditDialog(self, is_new=True)
        if dlg.exec() == QDialog.Accepted:
            name, voice, keys_str = dlg.get_data()
            if not name:
                QMessageBox.warning(self, "提示", "请输入操作命名"); return
            if not keys_str:
                QMessageBox.warning(self, "提示", "请输入按键序列"); return

            actions = self._parse_input(keys_str)
            if not actions:
                QMessageBox.warning(self, "错误", "按键解析失败"); return

            self.config.set_macro(name, actions)
            if voice:
                m = re.search(r'\[(.*?)\]', voice)
                clean = " ".join((m.group(1) if m else voice).split())
                if clean:
                    self.config.set_keyword(name, clean)
            try:
                self.config.save_all()
                self._refresh_cards()
            except IOError as e:
                QMessageBox.warning(self, "保存失败", str(e))

    def _on_edit(self, name):
        macros = self.config.get_macros_snapshot()
        keywords = self.config.get_keywords_snapshot()
        voice = keywords.get(name, "")
        keys = self._actions_to_str(macros.get(name, []))

        dlg = EditDialog(self, name=name, voice=voice, keys=keys, is_new=False)
        if dlg.exec() == QDialog.Accepted:
            _, new_voice, new_keys = dlg.get_data()
            actions = self._parse_input(new_keys)
            if actions:
                self.config.set_macro(name, actions)
            if new_voice:
                m = re.search(r'\[(.*?)\]', new_voice)
                clean = " ".join((m.group(1) if m else new_voice).split())
                if clean:
                    self.config.set_keyword(name, clean)
            try:
                self.config.save_all()
                self._refresh_cards()
            except IOError as e:
                QMessageBox.warning(self, "保存失败", str(e))

    def _on_delete(self, name):
        if QMessageBox.question(self, "确认", f"删除「{name}」？") == QMessageBox.Yes:
            self.config.remove_entry(name)
            try:
                self.config.save_all()
                self._refresh_cards()
            except IOError as e:
                QMessageBox.warning(self, "保存失败", str(e))

    # ── 监听 ──

    def toggle_listen(self):
        if self.listener and self.listener.is_running:
            self.listener.stop()
        else:
            self.listener = VoiceListener(
                on_trigger=lambda n: self.log_signal.emit(f"🎯 触发: {n}"),
                on_status=self.status_signal.emit
            )
            threading.Thread(target=self.listener.start, daemon=True).start()

    @Slot(str)
    def _handle_status(self, status):
        if status == "listening":
            self.listen_btn.setEnabled(False)
            self.listen_btn.setText("🔇  监听中...")
            self.listen_btn.setStyleSheet(self._listen_active_css())
            self.show_log_window()
            self.log_signal.emit("🟢 语音监听已启动")
        elif status == "stopped":
            self.listen_btn.setEnabled(True)
            self.listen_btn.setText("🔊  开启监听")
            self.listen_btn.setStyleSheet(self._listen_idle_css())
            self.log_signal.emit("🔴 语音监听已停止")
        elif status.startswith("error"):
            self.listen_btn.setEnabled(True)
            self.listen_btn.setText("🔊  开启监听")
            self.listen_btn.setStyleSheet(self._listen_idle_css())
            self.log_signal.emit(f"❌ {status}")

    @Slot(str)
    def _handle_log(self, msg):
        if self.log_window:
            self.log_window.append_log(msg)

    def show_log_window(self):
        if self.log_window is None or not self.log_window.isVisible():
            self.log_window = LogWindow()
            self.log_window.closed.connect(self._on_log_closed)
            self.log_window.show()
        else:
            self.log_window.raise_()

    def _on_log_closed(self):
        if self.listener and self.listener.is_running:
            self.listener.stop()

    def show_about(self):
        if self.about_window is None or not self.about_window.isVisible():
            self.about_window = AboutWindow()
            self.about_window.show()
            self.about_window.raise_()
        else:
            self.about_window.raise_()

    # ── 工具方法 ──

    @staticmethod
    def _actions_to_str(actions):
        parts = []
        for a in actions:
            if isinstance(a, (tuple, list)):
                parts.append(f"double_click:{a[1]}" if a[0] == "double_click" else f"({', '.join(a)})")
            else:
                parts.append(str(a))
        return " ".join(parts)

    @staticmethod
    def _parse_input(text):
        if not text:
            return []
        actions = []
        for part in re.findall(r'\([^)]+\)|\S+', text):
            part = part.strip()
            if not part:
                continue
            if part.startswith('(') and part.endswith(')'):
                keys = [k.strip().strip("'\"") for k in part[1:-1].split(',') if k.strip()]
                if keys:
                    actions.append(tuple(keys))
            elif part.startswith("double_click:"):
                actions.append(("double_click", part.split(":", 1)[1].strip().strip("'\"")))
            else:
                actions.append(part.strip("'\""))
        return actions


# ================= FlowLayout（卡片自动换行） =================

from PySide6.QtWidgets import QLayout
from PySide6.QtCore import QRect, QPoint

class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=16, spacing=12):
        super().__init__(parent)
        self.setContentsMargins(margin, margin, margin, margin)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        s = QSize()
        for item in self._items:
            s = s.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        s += QSize(m.left() + m.right(), m.top() + m.bottom())
        return s

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        effective = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
        x = effective.x()
        y = effective.y()
        row_height = 0

        for item in self._items:
            w = item.sizeHint()
            next_x = x + w.width() + self._spacing
            if next_x - self._spacing > effective.right() and row_height > 0:
                x = effective.x()
                y += row_height + self._spacing
                next_x = x + w.width() + self._spacing
                row_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), w))
            x = next_x
            row_height = max(row_height, w.height())

        return y + row_height - rect.y() + m.bottom()


# ================= 关于窗口 =================

class AboutWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🐉 关于斩龙")
        self.resize(500, 580)

        c = QWidget()
        c.setStyleSheet(f"background: {C['bg']};")
        self.setCentralWidget(c)
        lay = QVBoxLayout()
        lay.setSpacing(14)
        lay.setContentsMargins(24, 20, 24, 20)
        c.setLayout(lay)

        lay.addWidget(self._card(
            "⚠️  免责声明",
            "本工具通过模拟键盘实现语音控制，可能被反作弊系统判定为外挂。\n"
            "使用前请确认已了解风险，自行承担后果。\n仅用于技术学习与娱乐。",
            C['pink'], "#2d2033"
        ))
        lay.addWidget(self._card(
            "📢  交流 & 更新",
            "视频全网同名：乖宝喵呜呜\n🎮 玩家群：1070936439\n💻 开发群：810385945",
            C['blue'], "#1e2030"
        ))

        tip = QLabel("如果觉得有用，欢迎打赏支持 ❤️")
        tip.setAlignment(Qt.AlignCenter)
        tip.setStyleSheet(f"color: {C['subtext']}; font-size: 13px; background: transparent;")
        lay.addWidget(tip)

        img_row = QHBoxLayout()
        img_row.setAlignment(Qt.AlignCenter)
        img_row.setSpacing(20)
        for fname, title in [("wx.jpg", "微信"), ("zfb.jpg", "支付宝")]:
            p = get_resource_path(f"images/{fname}")
            if os.path.exists(p):
                pm = QPixmap(p).scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lb = QLabel(); lb.setPixmap(pm); lb.setAlignment(Qt.AlignCenter)
                img_row.addWidget(lb)
            else:
                ph = QLabel(f"[{title}]")
                ph.setAlignment(Qt.AlignCenter)
                ph.setStyleSheet(f"color:{C['dim']}; padding:20px; border:1px dashed {C['border']}; border-radius:8px;")
                img_row.addWidget(ph)
        lay.addLayout(img_row)
        lay.addStretch()

    @staticmethod
    def _card(title, body, accent, bg):
        lbl = QLabel(f"<p style='font-size:15px;font-weight:bold;color:{accent};'>{title}</p>"
                     f"<p style='font-size:12px;color:#cdd6f4;line-height:1.6;'>{body}</p>")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"background:{bg}; border:1px solid #313244; border-radius:10px; padding:16px;")
        return lbl


# ================= 启动 =================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(GLOBAL_STYLE)
    w = MacroTrainerUI()
    w.show()
    sys.exit(app.exec())
