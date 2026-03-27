# config_manager.py — 统一配置管理器
# 解决：路径硬编码、全局变量散落、listener 与 UI 配置不同步

import os
import sys
import re
import json
import threading

from utils.dialect_variants import generate_full_keywords_file


def get_resource_path(relative_path):
    """获取资源绝对路径，兼容 PyInstaller 打包"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)


class ConfigManager:
    """
    单例配置管理器。
    - 统一管理 skills.json 和 keywords_invoker.txt 的读写
    - 所有路径通过 get_resource_path() 计算，兼容 PyInstaller
    - 提供线程安全的读写操作
    - 支持变更回调，让 listener 实时感知配置变化
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # 路径统一管理
        self.skills_file = get_resource_path(os.path.join("utils", "skills.json"))
        self.keywords_file = get_resource_path(os.path.join("model", "keywords_invoker.txt"))
        self.model_dir = get_resource_path("model")
        self.tokens_file = get_resource_path(os.path.join("model", "tokens.txt"))

        # 配置数据
        self._data_lock = threading.Lock()
        self.invoker_macros = {}   # {name: actions}
        self.voice_keywords = {}   # {name: pinyin_str}

        # 变更回调列表
        self._on_change_callbacks = []

    def register_on_change(self, callback):
        """注册配置变更回调，listener 用这个来实时刷新"""
        self._on_change_callbacks.append(callback)

    def unregister_on_change(self, callback):
        """取消注册回调"""
        try:
            self._on_change_callbacks.remove(callback)
        except ValueError:
            pass

    def _notify_change(self):
        """通知所有监听者配置已变更"""
        for cb in self._on_change_callbacks:
            try:
                cb()
            except Exception:
                pass

    # ==========================================
    # 读取配置
    # ==========================================

    def load_config(self):
        """从文件加载配置，返回 (成功, 错误信息)"""
        with self._data_lock:
            self.invoker_macros = {}
            self.voice_keywords = {}

            # 1. 读取 skills.json
            error_msg = None
            if os.path.exists(self.skills_file):
                try:
                    with open(self.skills_file, "r", encoding="utf-8") as f:
                        self.invoker_macros = json.load(f)
                except Exception as e:
                    error_msg = f"读取 JSON 配置文件出错:\n{e}\n\n文件可能已损坏，将创建新配置。"
                    self.invoker_macros = {}

            # 2. 读取 keywords_invoker.txt
            # 注意：文件中包含方言变体行（_v1, _v2...）和阈值（:0.35）
            # 只读取原始关键词，变体由 dialect_variants 在写入时自动生成
            if os.path.exists(self.keywords_file):
                try:
                    with open(self.keywords_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line or "@" not in line:
                                continue
                            parts = line.split("@")
                            if len(parts) >= 2:
                                pinyin = parts[0].strip()
                                name_part = parts[1].strip()
                                # 去掉阈值后缀（如 ":0.35"）
                                if " :" in name_part:
                                    name_part = name_part.split(" :")[0].strip()
                                elif ":" in name_part:
                                    name_part = name_part.split(":")[0].strip()
                                # 跳过方言变体行（_v1, _v2...）
                                if re.search(r'_v\d+$', name_part):
                                    continue
                                # 清理旧格式后缀 _1, _2...
                                clean_name = re.sub(r'_\d+$', '', name_part)
                                self.voice_keywords[clean_name] = pinyin
                except Exception:
                    pass

        return (error_msg is None, error_msg)

    # ==========================================
    # 获取配置（线程安全的快照）
    # ==========================================

    def get_macros_snapshot(self):
        """返回当前 invoker_macros 的线程安全拷贝"""
        with self._data_lock:
            return dict(self.invoker_macros)

    def get_keywords_snapshot(self):
        """返回当前 voice_keywords 的线程安全拷贝"""
        with self._data_lock:
            return dict(self.voice_keywords)

    # ==========================================
    # 修改配置
    # ==========================================

    def set_macro(self, name, actions):
        """设置一个宏"""
        with self._data_lock:
            self.invoker_macros[name] = actions

    def remove_macro(self, name):
        """删除一个宏"""
        with self._data_lock:
            self.invoker_macros.pop(name, None)

    def set_keyword(self, name, pinyin):
        """设置一个语音关键词"""
        with self._data_lock:
            if pinyin:
                self.voice_keywords[name] = pinyin
            else:
                self.voice_keywords.pop(name, None)

    def remove_keyword(self, name):
        """删除一个语音关键词"""
        with self._data_lock:
            self.voice_keywords.pop(name, None)

    def remove_entry(self, name):
        """同时删除宏和关键词"""
        with self._data_lock:
            self.invoker_macros.pop(name, None)
            self.voice_keywords.pop(name, None)

    # ==========================================
    # 写入文件（保存全量配置）
    # ==========================================

    def save_all(self):
        """保存所有配置到文件，并通知 listener"""
        self._write_skills_file()
        self._write_keywords_file()
        self._notify_change()

    def _write_skills_file(self):
        """全量写入 skills.json"""
        with self._data_lock:
            clean_data = {}
            for name, actions in self.invoker_macros.items():
                cleaned_actions = []
                for action in actions:
                    if isinstance(action, tuple):
                        cleaned_actions.append(list(action))
                    elif isinstance(action, list):
                        cleaned_actions.append(action)
                    else:
                        cleaned_actions.append(action)
                clean_data[name] = cleaned_actions

        try:
            os.makedirs(os.path.dirname(self.skills_file), exist_ok=True)
            with open(self.skills_file, "w", encoding="utf-8") as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            raise IOError(f"无法写入配置文件:\n{e}")

    def _write_keywords_file(self):
        """全量写入 keywords_invoker.txt（自动生成方言变体 + 阈值）"""
        with self._data_lock:
            keywords_copy = dict(self.voice_keywords)

        try:
            os.makedirs(os.path.dirname(self.keywords_file), exist_ok=True)
            content = generate_full_keywords_file(keywords_copy)
            with open(self.keywords_file, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise IOError(f"无法写入关键词文件:\n{e}")

    # ==========================================
    # 模型路径便捷方法
    # ==========================================

    def get_model_path(self, filename):
        """获取模型文件的完整路径"""
        return os.path.join(self.model_dir, filename)

    def get_all_names(self):
        """获取所有已注册的名称（宏 + 关键词的并集）"""
        with self._data_lock:
            all_names = list(self.invoker_macros.keys())
            for name in self.voice_keywords.keys():
                if name not in all_names:
                    all_names.append(name)
            return all_names
