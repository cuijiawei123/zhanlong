# voice_listener.py（增强版 - VAD门控 + AGC调优 + 方言模糊匹配）

import threading
import queue
import time
import pyautogui
import sounddevice as sd
import sherpa_onnx
import numpy as np

from utils.config_manager import ConfigManager
from utils.fuzzy_matcher import FuzzyMatcher
from utils.threshold_tuner import ThresholdTuner

MIN_INTERVAL = 0.2
pyautogui.PAUSE = 0.1


class VoiceListener:
    def __init__(self, on_trigger=None, on_status=None):
        self.on_trigger = on_trigger or (lambda x: None)
        self.on_status = on_status or (lambda x: None)
        self.skill_queue = queue.Queue()
        self.executor_thread = None
        self.is_running = False
        self.kws = None
        self.kws_stream = None
        self._last_trigger_time = 0

        # ConfigManager 单例
        self.config = ConfigManager()
        self._macros_cache = {}

        # 模糊匹配器
        self._matcher = None

        # 动态阈值调优器
        self._tuner = ThresholdTuner()

        # VAD 相关
        self._vad = None
        self._vad_active = False          # 当前帧是否检测到人声
        self._vad_silence_frames = 0      # 连续静音帧计数
        self._VAD_SILENCE_THRESHOLD = 15  # 连续多少帧静音后认为说完了（约 150ms）

        # 线程安全锁
        self._audio_lock = threading.Lock()

        # AGC 参数（已调优：降低增益上限，减少噪音放大）
        self.target_volume = 0.25     # 目标音量（从 0.3 降到 0.25）
        self.min_gain = 1.0
        self.max_gain = 6.0           # 最大增益（从 15 降到 6，大幅减少噪音放大）
        self.smoothing_factor = 0.05  # 平滑系数（从 0.1 降到 0.05，更平稳）
        self.current_gain = 1.0

    def _refresh_macros(self):
        """从 ConfigManager 刷新宏配置（配置变更回调）"""
        self._macros_cache = self.config.get_macros_snapshot()
        if self._matcher:
            self._matcher.update(self._macros_cache)

    def _init_vad(self):
        """初始化 VAD（语音活动检测器）"""
        vad_model = self.config.get_model_path("silero_vad.onnx")

        import os
        if not os.path.exists(vad_model):
            # VAD 模型不存在，跳过 VAD（降级为无 VAD 模式）
            self._vad = None
            return False

        try:
            vad_config = sherpa_onnx.VadModelConfig()
            vad_config.silero_vad.model = vad_model
            vad_config.silero_vad.min_silence_duration = 0.15  # 最短静音判定时长(秒)
            vad_config.silero_vad.min_speech_duration = 0.1    # 最短语音判定时长(秒)
            vad_config.silero_vad.threshold = 0.4              # VAD 阈值
            vad_config.sample_rate = 16000
            vad_config.num_threads = 1

            self._vad = sherpa_onnx.VoiceActivityDetector(vad_config, buffer_size_in_seconds=3)
            return True
        except Exception:
            self._vad = None
            return False

    def start(self):
        # 初始化配置
        self._refresh_macros()
        self._matcher = FuzzyMatcher(self._macros_cache)
        self.config.register_on_change(self._refresh_macros)

        if self.is_running:
            return

        self.is_running = True

        try:
            self.on_status("starting")

            # 初始化 VAD
            has_vad = self._init_vad()

            # 初始化 KWS（使用 int8 量化模型，推理更快）
            self.kws = sherpa_onnx.KeywordSpotter(
                encoder=self.config.get_model_path("encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
                decoder=self.config.get_model_path("decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
                joiner=self.config.get_model_path("joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
                tokens=self.config.tokens_file,
                keywords_file=self.config.keywords_file,
                num_threads=4,
                sample_rate=16000,
                feature_dim=80,
                max_active_paths=10,
            )
            self.kws_stream = self.kws.create_stream()

            # 启动技能执行线程
            self.executor_thread = threading.Thread(target=self._execute_skills, daemon=True)
            self.executor_thread.start()

            vad_status = "VAD ✅" if has_vad else "VAD ❌ (模型未找到，降级运行)"
            self.on_status("listening")

            # 启动音频流
            with sd.InputStream(channels=1, samplerate=16000, dtype='float32', callback=self._audio_callback):
                while self.is_running:
                    time.sleep(0.01)

        except Exception as e:
            self.on_status(f"error: {str(e)}")
        finally:
            self.is_running = False
            self.config.unregister_on_change(self._refresh_macros)
            self.on_status("stopped")

    def _audio_callback(self, indata, frames, time_info, status):
        with self._audio_lock:
            if not self.is_running or self.kws is None or self.kws_stream is None:
                return

            samples = indata.flatten().astype('float32')

            # ==========================================
            # 第 1 层：VAD 门控（暂时禁用，待 API 适配后恢复）
            # ==========================================
            # TODO: sherpa_onnx VAD API 需要适配后重新启用
            # if self._vad is not None:
            #     ...

            # ==========================================
            # 第 2 层：AGC（已调优参数）
            # ==========================================
            rms = np.sqrt(np.mean(samples**2))

            if rms > 0.0001:
                ideal_gain = self.target_volume / rms
                clipped_gain = np.clip(ideal_gain, self.min_gain, self.max_gain)
                self.current_gain = (self.current_gain * (1 - self.smoothing_factor)
                                     + clipped_gain * self.smoothing_factor)
            else:
                self.current_gain = (self.current_gain * (1 - self.smoothing_factor)
                                     + 1.0 * self.smoothing_factor)

            samples = np.clip(samples * self.current_gain, -1.0, 1.0)

            # ==========================================
            # 第 3 层：KWS 关键词识别
            # ==========================================
            self.kws_stream.accept_waveform(16000, samples)

            while self.kws.is_ready(self.kws_stream):
                self.kws.decode_stream(self.kws_stream)

            result = self.kws.get_result(self.kws_stream)
            current_time = time.time()

            if result and (current_time - self._last_trigger_time) >= MIN_INTERVAL:
                self._last_trigger_time = current_time

                # 第 4 层：模糊匹配 — 将 KWS 结果映射回技能名
                matched_name = self._matcher.match(result) if self._matcher else result

                if matched_name:
                    # 第 5 层：动态阈值过滤 — 检测连续误触
                    approved = self._tuner.on_trigger(matched_name)
                    if approved:
                        self.skill_queue.put(approved)
                        self.on_trigger(approved)

    def _execute_skills(self):
        while self.is_running:
            try:
                skill_name = self.skill_queue.get(timeout=0.1)
                macros = self._macros_cache

                if skill_name in macros:
                    try:
                        for action in macros[skill_name]:
                            if isinstance(action, list):
                                first_elem = action[0]

                                if first_elem == "double_click":
                                    key = action[1]
                                    pyautogui.press(key)
                                    time.sleep(0.05)
                                    pyautogui.keyDown(key)
                                    time.sleep(0.05)
                                    pyautogui.keyUp(key)
                                else:
                                    modifiers = action[:-1]
                                    main_key = action[-1]

                                    for mod in modifiers:
                                        pyautogui.keyDown(mod)
                                        time.sleep(0.02)

                                    pyautogui.press(main_key)
                                    time.sleep(0.02)

                                    for mod in reversed(modifiers):
                                        pyautogui.keyUp(mod)
                                        time.sleep(0.02)
                            else:
                                pyautogui.press(str(action))

                    except Exception:
                        pass

                self.skill_queue.task_done()
            except queue.Empty:
                continue

    def stop(self):
        """外部调用此方法即可安全停止监听"""
        self.is_running = False
