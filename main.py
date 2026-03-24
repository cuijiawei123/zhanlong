import sys
import os
import queue
import threading
import time
import pyautogui
import re
import json  # <--- 新增导入 json
from utils.voice_engine import start_recording, stop_and_get_result
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QListWidget, QGroupBox, QMessageBox, QAbstractScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QMainWindow
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from utils.voice_listener import VoiceListener
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, Slot, QTimer

from utils.log_window import LogWindow

# ================= 配置 =================
# 🔥 修改点 1: 文件名改为 .json
SKILLS_FILE = "./utils/skills.json"  
KEYWORDS_FILE = "./model/keywords_invoker.txt"
INVOKER_MACROS = {}      # {name: actions}
VOICE_KEYWORDS = {}      # {name: pinyin_str}
skill_queue = queue.Queue()
executor_thread = None


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)



# ================= UI 界面 =================

class MacroTrainerUI(QWidget):
    log_signal = Signal(str)
    status_signal = Signal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle("宏配置器 (JSON 单行保存版)")
        self.resize(900, 650) 
        self.setMinimumSize(750, 500)
        self.listener = None
        self.log_signal.connect(self._handle_log)
        self.status_signal.connect(self._handle_status)
        self.load_config()
   
        self.log_window = None
        self._voice_thread = None
        self._voice_result = None
        self._is_recording = False
        
        self.about_window = None
        QTimer.singleShot(100, self.show_about)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setSpacing(15) 
        main_layout.setContentsMargins(20, 20, 20, 20)

        # --- 1. 操作命名 (保持不变) ---
        row1 = QHBoxLayout()
        lbl1 = QLabel("操作命名:")
        lbl1.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.input_name = QLineEdit()
        self.input_name.setPlaceholderText("随意命名，方便记忆，与发音无关")
        self.input_name.setStyleSheet("padding: 6px; font-size: 11pt;")
        row1.addWidget(lbl1)
        row1.addWidget(self.input_name)
        main_layout.addLayout(row1)

        # --- 2. 录入按键 (保持不变) ---
        row2 = QHBoxLayout()
        lbl2 = QLabel("录入按键:")
        lbl2.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        self.input_keys = QLineEdit()
        self.input_keys.setPlaceholderText("按键之间用空格隔开 例：a b c double_click:space 组合键用括号括起来，括号内不要有空格 (ctrl,c)")
        self.input_keys.setStyleSheet("padding: 6px; font-size: 11pt; font-family: Consolas;")
        row2.addWidget(lbl2)
        row2.addWidget(self.input_keys)
        main_layout.addLayout(row2)

        # --- 3. 录入语音 (保持不变) ---
        row3 = QHBoxLayout()
        lbl3 = QLabel("录入语音:")
        lbl3.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        
        self.input_voice = QLineEdit()
        self.input_voice.setPlaceholderText("(长按话筒录入，开始和结束时保持 1s 静音)")
        self.input_voice.setStyleSheet("padding: 6px; font-size: 11pt;")
        
        self.btn_mic = QPushButton("️🎤")
        self.btn_mic.setFixedSize(50, 50)
        self.btn_mic.setStyleSheet("""
            QPushButton { 
                background: #f0f0f0; 
                border-radius: 25px; 
                font-size: 24pt; 
                border: 2px solid #ccc;
            }
            QPushButton:hover { background: #ffeb3b; border-color: #fbc02d; }
            QPushButton:pressed { background: #ff4d4d; border-color: #cc0000; color: white; }
            QPushButton[active="true"] { background: #ff4d4d; border-color: #cc0000; color: white; }
        """)
        
        self.btn_mic.pressed.connect(self.on_mic_pressed)
        self.btn_mic.released.connect(self.on_mic_released)
        
        row3.addWidget(lbl3)
        row3.addWidget(self.input_voice)
        row3.addWidget(self.btn_mic)
        main_layout.addLayout(row3)

        # --- 4. 按钮区 (保持不变) ---
        btn_layout = QHBoxLayout()
        self.btn_save_all = QPushButton("💾 保存") 
        self.btn_save_all.setStyleSheet("background: #28a745; color: white; font-weight: bold; padding: 8px; border-radius: 4px; font-size: 12pt;")
        self.btn_save_all.clicked.connect(self.save_macro) 
        
        self.listen_btn = QPushButton("🔊 开启语音监听")
        self.listen_btn.setStyleSheet("background: #007bff; color: white; font-weight: bold; padding: 8px; border-radius: 4px; font-size: 12pt;")
        self.listen_btn.clicked.connect(self.toggle_listen)
        
            
        
        btn_layout.addWidget(self.btn_save_all)
        btn_layout.addWidget(self.listen_btn)
        main_layout.addLayout(btn_layout)
        
        
      
        
        
        

        # --- 5. 列表展示 (🔥 核心修改：5 列 + 单行保存) ---
        list_group = QGroupBox("📋 已绑定按键列表 (可以单击修改语音和按键，编辑后点击行内保存)")
        list_layout = QVBoxLayout()
        list_group.setLayout(list_layout)
        
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5) # 名称 | 语音 | 按键 | 保存 | 删除
        self.table_widget.setHorizontalHeaderLabels(["名称", "语音输入", "键盘输入", "", ""])
        
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)         
        header.setSectionResizeMode(1, QHeaderView.Stretch)       
        header.setSectionResizeMode(2, QHeaderView.Stretch)       
        header.setSectionResizeMode(3, QHeaderView.Fixed)         
        header.setSectionResizeMode(4, QHeaderView.Fixed)         
        
        self.table_widget.setColumnWidth(0, 120)  
        self.table_widget.setColumnWidth(3, 70)   
        self.table_widget.setColumnWidth(4, 70)   
        
        self.table_widget.setFont(QFont("Consolas", 10))
        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.setStyleSheet("""
            QTableWidget { gridline-color: #ddd; border: 1px solid #ccc; background: white; }
            QTableWidget::item { padding: 5px; border: none; }
            QTableWidget::item:focus { background: #e3f2fd; outline: none; }
            QHeaderView::section { background: #f0f0f0; padding: 4px; border: 1px solid #ddd; font-weight: bold; }
        """)
        
        self.table_widget.cellChanged.connect(self.on_cell_changed)
        
        self.refresh_list()
        list_layout.addWidget(self.table_widget)
        main_layout.addWidget(list_group)
      
    def show_about(self):
        if self.about_window is None or not self.about_window.isVisible():
            self.about_window = AboutWindow()
            self.about_window.show()
            self.about_window.raise_()
            self.about_window.activateWindow()
        else:
            self.about_window.raise_()
            self.about_window.activateWindow()

    def show_log_window(self):
            if self.log_window is None or not self.log_window.isVisible():
                self.log_window = LogWindow()
                self.log_window.closed.connect(self.on_log_window_closed)
                self.log_window.show()
            else:
                self.log_window.raise_()
                self.log_window.activateWindow()

    def on_log_window_closed(self):
        """当日志窗口关闭时，强制停止监听"""
        if self.listener and self.listener.is_running:
            self.listener.stop()
    @Slot(str)
    def _handle_log(self, msg):
        if self.log_window:
            self.log_window.append_log(msg)

    @Slot(str)
    def _handle_status(self, status):
        if status == "listening":
            self.listen_btn.setEnabled(False)
            self.listen_btn.setText("🔇 监听中...")
            self.listen_btn.setStyleSheet("""
                QPushButton {
                    background: #dc3545;
                    color: white;
                    border: none;
                    padding: 10px 30px;
                    border-radius: 8px;
                    font-size: 11pt;
                }
                QPushButton:hover {
                    background: #c82333;
                }
            """)
            self.show_log_window()
            self.log_signal.emit("🟢 语音监听已启动")

        elif status == "stopped":
            self.listen_btn.setEnabled(True)
            self.listen_btn.setText("🔊 开启语音监听")
            self.listen_btn.setStyleSheet("""
                QPushButton {
                    background: #007bff;
                    color: white;
                    border: none;
                    padding: 10px 30px;
                    border-radius: 8px;
                    font-size: 11pt;
                }
              
            """)
            self.log_signal.emit("🔴 语音监听已停止")

        elif status.startswith("error"):
            self.listen_btn.setEnabled(True)
            self.listen_btn.setText("🔊 开启语音监听")
            self.log_signal.emit(f"❌ 错误: {status}")

    def toggle_listen(self):
        if self.listener and self.listener.is_running:
            self.listener.stop()
        else:
            self.listener = VoiceListener(
                on_trigger=lambda name: self.log_signal.emit(f"🎯 触发技能: {name}"),
                on_status=self.status_signal.emit
            )
            thread = threading.Thread(target=self.listener.start, daemon=True)
            thread.start()

    # ==========================================
    # 🔥 表格特有逻辑
    # ==========================================

    def refresh_list(self):
        """刷新表格数据"""
        self.table_widget.setRowCount(0)
        
        all_names = list(INVOKER_MACROS.keys())
        for name in VOICE_KEYWORDS.keys():
            if name not in all_names:
                all_names.append(name)
        
        for name in all_names:
            row_pos = self.table_widget.rowCount()
            self.table_widget.insertRow(row_pos)
            
            # 1. 名称
            item_name = QTableWidgetItem(name)
            item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable) 
            item_name.setToolTip("名称不可修改，如需改名请删除后重新添加")
            self.table_widget.setItem(row_pos, 0, item_name)
            # 2. 语音
            pinyin = VOICE_KEYWORDS.get(name, "")
            item_voice = QTableWidgetItem(pinyin)
            item_voice.setFlags(item_voice.flags() | Qt.ItemIsEditable)
            self.table_widget.setItem(row_pos, 1, item_voice)
         
            # 3. 按键
            actions = INVOKER_MACROS.get(name, [])
            str_actions = []
            for a in actions:
                # 🔥 修改点：兼容 list 和 tuple (虽然存进去是 list，但内存里可能还有旧 tuple)
                if isinstance(a, (tuple, list)):
                    if a[0] == "double_click":
                        str_actions.append(f"double_click:{a[1]}")
                    else:
                        str_actions.append(f"({', '.join(a)})")
                else:
                    str_actions.append(str(a))
            keys_str = " ".join(str_actions)
  
            item_keys = QTableWidgetItem(keys_str)
            item_keys.setFlags(item_keys.flags() | Qt.ItemIsEditable)
            self.table_widget.setItem(row_pos, 2, item_keys)
            
            # 4. 单行保存按钮
            btn_save_row = QPushButton("保存")
            btn_save_row.setToolTip("仅保存此行修改到文件")
            btn_save_row.setStyleSheet("""
             
                QPushButton { 
                    background: #28a745; 
                    color: white; 
                    border-radius: 4px; 
                    font-weight: bold; 
                    font-size: 8pt;
                    padding: 4px 10px;
                }
                QPushButton:hover { background: #218838; }
                QPushButton:pressed { background: #1e7e34; }
            """)
            btn_save_row.clicked.connect(lambda checked, r=row_pos: self.save_single_row(r))
            
            container_save = QWidget()
            layout_save = QHBoxLayout(container_save)
            layout_save.addWidget(btn_save_row)
            layout_save.setAlignment(Qt.AlignCenter)
            layout_save.setContentsMargins(0,0,0,0)
            self.table_widget.setCellWidget(row_pos, 3, container_save)

            # 5. 删除按钮
            btn_delete = QPushButton("删除")
            btn_delete.setToolTip("删除此行")
            btn_delete.setStyleSheet("""
                QPushButton { 
                    background: #dc3545; 
                    color: white; 
                    border-radius: 4px; 
                    font-weight: bold; 
                    font-size: 8pt;
                    padding: 4px 10px;
                }
                QPushButton:hover { background: #c82333; }
                QPushButton:pressed { background: #bd2130; }
            """)
            btn_delete.clicked.connect(lambda checked, r=row_pos: self.delete_row(r))
            
            container_del = QWidget()
            layout_del = QHBoxLayout(container_del)
            layout_del.addWidget(btn_delete)
            layout_del.setAlignment(Qt.AlignCenter)
            layout_del.setContentsMargins(0,0,0,0)
            self.table_widget.setCellWidget(row_pos, 4, container_del)

    def save_single_row(self, row):
        """只保存当前行的数据到文件"""
        name_item = self.table_widget.item(row, 0)
        voice_item = self.table_widget.item(row, 1)
        keys_item = self.table_widget.item(row, 2)
        
        if not name_item:
            return
            
        name = name_item.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "名称不能为空")
            return

        current_name = name
        original_name = name_item.data(Qt.UserRole)
        if original_name is None: original_name = current_name

        # 更新语音内存
        if voice_item:
            val = voice_item.text().strip()
            if val: VOICE_KEYWORDS[current_name] = val
            else: VOICE_KEYWORDS.pop(current_name, None)
            if current_name != original_name: VOICE_KEYWORDS.pop(original_name, None)

        # 更新按键内存
        if keys_item:
            val = keys_item.text().strip()
            actions = self.parse_user_input(val)
            if actions: INVOKER_MACROS[current_name] = actions
            else: INVOKER_MACROS.pop(current_name, None)
            if current_name != original_name: INVOKER_MACROS.pop(original_name, None)
        
        if current_name != original_name:
            name_item.setData(Qt.UserRole, current_name)

        # 写入 JSON 文件
        self.write_skills_file_full()
        
        # 写入关键词文件
        self.write_keywords_file_full()

        QMessageBox.information(self, "成功", f"已保存：{name}")

    def on_cell_changed(self, row, col):
        """单元格改变仅更新内存，不写文件"""
        name_item = self.table_widget.item(row, 0)
        voice_item = self.table_widget.item(row, 1)
        keys_item = self.table_widget.item(row, 2)
        
        if not name_item or not name_item.text().strip():
            return
            
        current_name = name_item.text().strip()
        original_name = name_item.data(Qt.UserRole)
        if original_name is None: original_name = current_name

        if voice_item:
            val = voice_item.text().strip()
            if val: VOICE_KEYWORDS[current_name] = val
            else: VOICE_KEYWORDS.pop(current_name, None)
            if current_name != original_name: VOICE_KEYWORDS.pop(original_name, None)

        if keys_item:
            val = keys_item.text().strip()
            actions = self.parse_user_input(val)
            if actions: INVOKER_MACROS[current_name] = actions
            else: INVOKER_MACROS.pop(current_name, None)
            if current_name != original_name: INVOKER_MACROS.pop(original_name, None)
        
        if current_name != original_name:
            name_item.setData(Qt.UserRole, current_name)

    def delete_row(self, row):
        """删除指定行"""
        name_item = self.table_widget.item(row, 0)
        if not name_item: return
        name = name_item.text().strip()
        
        reply = QMessageBox.question(self, "确认删除", f"确定要删除 '{name}' 吗？")
        if reply == QMessageBox.Yes:
            INVOKER_MACROS.pop(name, None)
            VOICE_KEYWORDS.pop(name, None)
            self.table_widget.removeRow(row)
            self.write_skills_file_full()
            self.write_keywords_file_full()

    # ==========================================
    # 🔥 话筒逻辑 (保持不变)
    # ==========================================



    def on_mic_pressed(self):
        if self._is_recording: return
        if not start_recording():
            QMessageBox.critical(self, "错误", "录音启动失败！")
            return
        self._is_recording = True
        self.btn_mic.setProperty("active", "true")
        self.btn_mic.style().unpolish(self.btn_mic)
        self.btn_mic.style().polish(self.btn_mic)
        self.input_voice.setText("🎤 正在录音...")
        self.input_voice.setStyleSheet("padding: 6px; font-size: 11pt; color: #ff4d4d; font-weight: bold;")

    def on_mic_released(self):
        if not self._is_recording: return
        self.btn_mic.setProperty("active", "false")
        self.btn_mic.style().unpolish(self.btn_mic)
        self.btn_mic.style().polish(self.btn_mic)
        self.input_voice.setText("⏳ 识别中...")
        QApplication.processEvents()
        
        raw_text, pinyin = stop_and_get_result()
        
        if raw_text == "错误":
            display = f"❌ {pinyin}"
            style = "color: red;"
        elif not raw_text:
            display = "未检测到语音"
            style = "color: gray;"
        else:
            display = f"{pinyin}"
            style = "color: green; font-weight: bold;"
        
        self.input_voice.setText(display)
        self.input_voice.setStyleSheet(f"padding: 6px; font-size: 11pt; {style}")
        self._is_recording = False

    # ==========================================
    # 🔥 文件读写逻辑 (🔥 核心修改区域)
    # ==========================================

    def load_config(self):
        global INVOKER_MACROS, VOICE_KEYWORDS
        INVOKER_MACROS = {}
        VOICE_KEYWORDS = {}
        
        # 🔥 修改点 2: 读取 JSON 文件
        if os.path.exists(SKILLS_FILE):
            try:
                with open(SKILLS_FILE, "r", encoding="utf-8") as f:
                    # 直接加载为字典，JSON 中的数组会自动变成 Python 的 list
                    INVOKER_MACROS = json.load(f)
        
            except Exception as e:
                QMessageBox.warning(self, "加载失败", f"读取 JSON 配置文件出错:\n{e}\n\n文件可能已损坏，将创建新配置。")
                INVOKER_MACROS = {}

        # 关键词文件读取逻辑不变
        if os.path.exists(KEYWORDS_FILE):
            with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or "@" not in line: continue
                    parts = line.split("@")
                    if len(parts) >= 2:
                        pinyin = parts[0].strip()
                        name_full = parts[1].strip()
                        clean_name = re.sub(r'_\d+$', '', name_full)
                        VOICE_KEYWORDS[clean_name] = pinyin

    def parse_user_input(self, text):
        """
        正确解析：a (ctrl, c)  ->  ['a', ('ctrl', 'c')]
        注意：这里依然生成元组，因为在内存中处理方便。
        写入文件时会在 write_skills_file_full 中统一转为 list。
        """
        actions = []
        pattern = re.compile(r'\([^)]+\)|\S+')
        matches = pattern.findall(text)
        
        for part in matches:
            part = part.strip()
            if not part:
                continue
                
            if part.startswith('(') and part.endswith(')'):
                content = part[1:-1]
                raw_keys = content.split(',')
                clean_keys = []
                for k in raw_keys:
                    k = k.strip()
                    if len(k) >= 2:
                        if (k.startswith("'") and k.endswith("'")) or \
                        (k.startswith('"') and k.endswith('"')):
                            k = k[1:-1]
                    if k:
                        clean_keys.append(k)
                if clean_keys:
                    actions.append(tuple(clean_keys)) # 内存中暂时保留元组
                else:
                    pass
            elif part.startswith("double_click:"):
                key = part.split(":", 1)[1].strip()
                if len(key) >= 2 and ((key.startswith("'") and key.endswith("'")) or (key.startswith('"') and key.endswith('"'))):
                    key = key[1:-1]
                actions.append(("double_click", key))
            else:
                clean_part = part
                if len(clean_part) >= 2:
                    if (clean_part.startswith("'") and clean_part.endswith("'")) or \
                    (clean_part.startswith('"') and clean_part.endswith('"')):
                        clean_part = clean_part[1:-1]
                actions.append(clean_part)

        return actions
        
    
    def write_skills_file_full(self):
        """🔥 修改点 3: 全量写入 JSON 文件，并自动转换元组为列表"""
        clean_data = {}
        
        # 遍历内存中的数据，将所有的 tuple 转换为 list
        for name, actions in INVOKER_MACROS.items():
            cleaned_actions = []
            for action in actions:
                if isinstance(action, tuple):
                    cleaned_actions.append(list(action)) # 元组转列表
                elif isinstance(action, list):
                    cleaned_actions.append(action)
                else:
                    cleaned_actions.append(action)
            clean_data[name] = cleaned_actions

        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(SKILLS_FILE), exist_ok=True)
            
            with open(SKILLS_FILE, "w", encoding="utf-8") as f:
                # 写入 JSON，ensure_ascii=False 支持中文，indent=4 美化格式
                json.dump(clean_data, f, ensure_ascii=False, indent=4)
  
        except Exception as e:

            QMessageBox.warning(self, "保存失败", f"无法写入文件:\n{e}")

    def write_keywords_file_full(self):
        """全量写入 keywords_invoker.txt"""
        os.makedirs("./model", exist_ok=True)
        lines = []
        for name, pinyin in VOICE_KEYWORDS.items():
            if pinyin:
                lines.append(f"{pinyin} @{name}\n")
        
        with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines)

    def update_keywords_file(self, pinyin_text, skill_name):
        # 保留原有的追加逻辑
        if not pinyin_text or not skill_name: return False
        keywords_path = KEYWORDS_FILE
        os.makedirs("./model", exist_ok=True)
        
        existing_lines = []
        if os.path.exists(keywords_path):
            with open(keywords_path, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()
        
        max_index = 0
        new_lines = []
        
        for line in existing_lines:
            line_stripped = line.strip()
            if not line_stripped: continue
            
            if f"@{skill_name}_" in line_stripped or f"@{skill_name}" == line_stripped.split('@')[-1].split('_')[0]:
                try:
                    suffix = line_stripped.split('@')[1] 
                    if "_" in suffix:
                        name_part, num_part = suffix.rsplit("_", 1)
                        if name_part == skill_name and num_part.isdigit():
                            idx = int(num_part)
                            if idx > max_index: max_index = idx
                            new_lines.append(line_stripped + "\n") 
                            continue
                    elif suffix == skill_name:
                        max_index = max(max_index, 0)
                        new_lines.append(line_stripped + "\n")
                        continue
                except Exception: pass
            new_lines.append(line_stripped + "\n")

        new_index = max_index + 1
        new_entry = f"{pinyin_text} @{skill_name}_{new_index}\n"
        new_lines.append(new_entry)
        
        with open(keywords_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True

    def save_macro(self):
        # 顶部的“保存所有”按钮逻辑
        name = self.input_name.text().strip()
        keys_str = self.input_keys.text().strip()
        voice_pinyin = self.input_voice.text().strip()

        if name and keys_str:
            actions = self.parse_user_input(keys_str)
            if not actions:
                QMessageBox.warning(self, "错误", "按键解析失败。")
                return
            
            INVOKER_MACROS[name] = actions
            
            if voice_pinyin:
                match = re.search(r'\[(.*?)\]', voice_pinyin)
                clean_pinyin = match.group(1) if match else voice_pinyin
                clean_pinyin = " ".join(clean_pinyin.split())
                if clean_pinyin:
                    VOICE_KEYWORDS[name] = clean_pinyin
                    self.update_keywords_file(clean_pinyin, name)
            
            self.refresh_list()
            self.input_name.clear()
            self.input_keys.clear()
            self.input_voice.clear()
            QMessageBox.information(self, "成功", f"已添加：{name}")

        self.write_skills_file_full()
        self.write_keywords_file_full()



class AboutWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ℹ️ 关于 & 打赏")
        self.resize(600, 750)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout()
        central.setLayout(layout)

        disclaimer = QLabel(
            "<p style='color: #d32f2f; font-weight: bold; font-size: 20pt;'>⚠️ 免责声明</p>"
            "<p style='color: black; font-size: 14pt;'>本工具通过模拟键盘按键实现语音控制，可能被部分游戏反作弊系统判定为<b>外挂</b>。</p>"
            "<p style='color: black; font-size: 14pt;'>使用前请确认您已了解风险，并自行承担一切后果。</p>"
            "<p style='color: black; font-size: 14pt;'>本软件仅用于技术学习与娱乐，禁止用于商业用途。</p>"
        )
        disclaimer.setWordWrap(True)
        disclaimer.setStyleSheet("padding: 15px; background-color: #ffebee; border-radius: 8px; margin-bottom: 15px;")
        layout.addWidget(disclaimer)

        qq_info = QLabel(
            "<p style='color: #4a148c; font-size: 16pt;'>📢 后续更新 & 交流</p>"
            "<p style='font-size: 14pt;'>视频平台全网同名：<b>乖宝喵呜呜</b>  </p>"
            "<p style='font-size: 14pt;'>欢迎加入 QQ 群获取最新版本、反馈问题：</p>"
            "<p style='font-size: 14pt;'>玩家群：1070936439 </p>"
            "<p style='font-size: 14pt;'>开发群：810385945 </p>"
        )
        qq_info.setWordWrap(True)
        qq_info.setStyleSheet("margin-bottom: 20px;")
        layout.addWidget(qq_info)

        donate_text = QLabel(
            "<p style='text-align: center; font-size: 14pt; color: #1a5f7a;'>"
            "如果给您带来了新奇的游戏体验，欢迎打赏支持一下 ~ "
            "谢谢~"
            "</p>"
        )
        donate_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(donate_text)

        donate_layout = QHBoxLayout()
        donate_layout.setAlignment(Qt.AlignCenter)
        donate_layout.setSpacing(20)

        for name, title in [("wx.jpg", "微信打赏"), ("zfb.jpg", "支付宝打赏")]:
            img_path = get_resource_path(f"images/{name}")
            if os.path.exists(img_path):
                pixmap = QPixmap(img_path).scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_label = QLabel()
                img_label.setPixmap(pixmap)
                img_label.setAlignment(Qt.AlignCenter)
                donate_layout.addWidget(img_label)
            else:
                placeholder = QLabel(f"[{title}]\n（图片未找到）")
                placeholder.setAlignment(Qt.AlignCenter)
                placeholder.setStyleSheet("color: gray; font-size: 10pt;")
                donate_layout.addWidget(placeholder)

        layout.addLayout(donate_layout)



  
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MacroTrainerUI()
    window.show()
    sys.exit(app.exec())