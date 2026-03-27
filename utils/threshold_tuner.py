# threshold_tuner.py — 动态阈值自动调优
# 统计每个关键词的触发模式，自动调整阈值减少误触

import time
import json
import os
import threading
from collections import defaultdict

from utils.config_manager import ConfigManager


class ThresholdTuner:
    """
    动态阈值调优器。

    原理：
    - 记录每个关键词的触发时间戳
    - 如果某个关键词在短时间内被连续触发（>3次/5秒），判定为误触
    - 自动提高该关键词的阈值（写入 keywords_invoker.txt）
    - 长期无误触则缓慢降低阈值（恢复灵敏度）

    同时记录统计数据到本地文件，供用户查看。
    """

    def __init__(self):
        self.config = ConfigManager()
        self._lock = threading.Lock()

        # 触发记录：{keyword: [timestamp, timestamp, ...]}
        self._trigger_times = defaultdict(list)

        # 阈值调整记录：{keyword: current_threshold_delta}
        # delta > 0 表示比原始阈值更严格
        self._threshold_deltas = defaultdict(float)

        # 统计数据：{keyword: {total: int, suppressed: int}}
        self._stats = defaultdict(lambda: {"total": 0, "suppressed": 0})

        # 配置
        self.BURST_WINDOW = 5.0       # 连续触发检测窗口（秒）
        self.BURST_THRESHOLD = 3      # 窗口内触发超过此数视为误触
        self.PENALTY_STEP = 0.05      # 每次误触提高的阈值步长
        self.MAX_PENALTY = 0.25       # 最大惩罚值
        self.RECOVERY_INTERVAL = 300  # 每隔多少秒恢复一次（5分钟）
        self.RECOVERY_STEP = 0.01     # 每次恢复降低的阈值步长

        # 恢复定时器
        self._recovery_timer = None
        self._start_recovery_timer()

        # 加载历史数据（存到跨平台用户数据目录）
        self._stats_file = self._get_data_file("trigger_stats.json")
        self._load_stats()

    @staticmethod
    def _get_data_file(filename):
        """获取跨平台用户数据目录下的文件路径。
        - Windows: %APPDATA%/Zhanlong/
        - macOS:   ~/Library/Application Support/Zhanlong/
        - Linux:   ~/.local/share/Zhanlong/
        """
        import platform
        system = platform.system()
        if system == "Windows":
            base = os.environ.get("APPDATA", os.path.expanduser("~"))
            data_dir = os.path.join(base, "Zhanlong")
        elif system == "Darwin":
            data_dir = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Zhanlong")
        else:  # Linux 及其他
            xdg = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
            data_dir = os.path.join(xdg, "Zhanlong")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, filename)

    def on_trigger(self, keyword):
        """
        每次 KWS 触发时调用。

        返回：
            str|None — 如果应该执行返回关键词名，如果判定为误触返回 None
        """
        with self._lock:
            now = time.time()
            self._stats[keyword]["total"] += 1

            # 记录时间戳
            self._trigger_times[keyword].append(now)

            # 清理过期时间戳（只保留窗口内的）
            cutoff = now - self.BURST_WINDOW
            self._trigger_times[keyword] = [
                t for t in self._trigger_times[keyword] if t > cutoff
            ]

            # 检测连续触发（误触特征）
            recent_count = len(self._trigger_times[keyword])
            if recent_count > self.BURST_THRESHOLD:
                # 判定为误触，施加惩罚
                self._threshold_deltas[keyword] = min(
                    self._threshold_deltas[keyword] + self.PENALTY_STEP,
                    self.MAX_PENALTY
                )
                self._stats[keyword]["suppressed"] += 1
                self._save_stats()

                # 触发配置重写（提高阈值）
                self._apply_threshold_changes()
                return None  # 抑制此次触发

            return keyword

    def get_stats(self):
        """获取统计数据（给前端展示用）"""
        with self._lock:
            result = {}
            for kw, stat in self._stats.items():
                result[kw] = {
                    "total": stat["total"],
                    "suppressed": stat["suppressed"],
                    "penalty": round(self._threshold_deltas.get(kw, 0), 3),
                    "accuracy": round(
                        (1 - stat["suppressed"] / max(stat["total"], 1)) * 100, 1
                    )
                }
            return result

    def reset_keyword(self, keyword):
        """重置某个关键词的统计和惩罚"""
        with self._lock:
            self._trigger_times.pop(keyword, None)
            self._threshold_deltas.pop(keyword, None)
            self._stats.pop(keyword, None)
            self._save_stats()

    def _apply_threshold_changes(self):
        """将阈值变更应用到 keywords_invoker.txt"""
        # 读取当前关键词文件，修改阈值，重写
        try:
            kw_file = self.config.keywords_file
            if not os.path.exists(kw_file):
                return

            with open(kw_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            new_lines = []
            for line in lines:
                stripped = line.strip()
                if not stripped or "@" not in stripped:
                    new_lines.append(line)
                    continue

                # 解析：pinyin @name :threshold
                parts = stripped.split("@")
                if len(parts) < 2:
                    new_lines.append(line)
                    continue

                pinyin = parts[0].strip()
                name_part = parts[1].strip()

                # 提取原始阈值
                orig_threshold = 0.2
                name_clean = name_part
                if " :" in name_part:
                    name_clean, thresh_str = name_part.rsplit(" :", 1)
                    try:
                        orig_threshold = float(thresh_str)
                    except ValueError:
                        pass
                elif ":" in name_part:
                    name_clean, thresh_str = name_part.rsplit(":", 1)
                    try:
                        orig_threshold = float(thresh_str)
                    except ValueError:
                        pass

                # 查看是否有惩罚（用基础名匹配）
                import re
                base_name = re.sub(r'_v\d+$', '', name_clean.strip())
                delta = self._threshold_deltas.get(base_name, 0)

                if delta > 0:
                    new_threshold = min(orig_threshold + delta, 0.8)
                    new_lines.append(f"{pinyin} @{name_clean.strip()} :{new_threshold:.2f}\n")
                else:
                    new_lines.append(line)

            with open(kw_file, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

        except Exception:
            pass  # 阈值调整失败不应影响正常运行

    def _start_recovery_timer(self):
        """定期恢复阈值（降低惩罚）"""
        def recover():
            with self._lock:
                changed = False
                for kw in list(self._threshold_deltas.keys()):
                    if self._threshold_deltas[kw] > 0:
                        self._threshold_deltas[kw] = max(
                            0, self._threshold_deltas[kw] - self.RECOVERY_STEP
                        )
                        changed = True
                    if self._threshold_deltas[kw] <= 0:
                        del self._threshold_deltas[kw]

                if changed:
                    self._apply_threshold_changes()
                    self._save_stats()

            # 继续定时
            self._recovery_timer = threading.Timer(self.RECOVERY_INTERVAL, recover)
            self._recovery_timer.daemon = True
            self._recovery_timer.start()

        self._recovery_timer = threading.Timer(self.RECOVERY_INTERVAL, recover)
        self._recovery_timer.daemon = True
        self._recovery_timer.start()

    def _load_stats(self):
        """从文件加载历史统计"""
        try:
            if os.path.exists(self._stats_file):
                with open(self._stats_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for kw, stat in data.get("stats", {}).items():
                        self._stats[kw] = stat
                    for kw, delta in data.get("deltas", {}).items():
                        self._threshold_deltas[kw] = delta
        except Exception:
            pass

    def _save_stats(self):
        """保存统计到文件"""
        try:
            os.makedirs(os.path.dirname(self._stats_file), exist_ok=True)
            with open(self._stats_file, "w", encoding="utf-8") as f:
                json.dump({
                    "stats": dict(self._stats),
                    "deltas": dict(self._threshold_deltas),
                    "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
