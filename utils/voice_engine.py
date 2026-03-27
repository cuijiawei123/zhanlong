# voice_engine.py (优化版 - ConfigManager 统一路径)

import sherpa_onnx
import sounddevice as sd
import numpy as np
import os
import sys
import threading

from utils.config_manager import ConfigManager

# 全局模型缓存
_recognizer = None
_token_set = None
_config = ConfigManager()


def _load_model():
    """单例模式加载模型"""
    global _recognizer, _token_set
    if _recognizer is not None:
        return True

    model_dir = _config.model_dir
    tokens_file = _config.tokens_file

    if not os.path.exists(model_dir):
        return False

    required_files = [
        "encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
        "decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
        "joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
        "tokens.txt"
    ]

    for f in required_files:
        if not os.path.exists(_config.get_model_path(f)):
            return False

    try:
        _recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=_config.get_model_path("encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            decoder=_config.get_model_path("decoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            joiner=_config.get_model_path("joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx"),
            tokens=tokens_file,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            num_threads=2,
        )

        with open(tokens_file, encoding="utf-8") as f:
            _token_set = {line.split()[0] for line in f if line.strip()}

        return True
    except Exception:
        return False


def _tokenize_text(text):
    """将中文文本转换为 Token (拼音) 序列"""
    if not text or not _token_set:
        return []

    tokens = []
    i = 0
    max_len = max(len(t) for t in _token_set) if _token_set else 1

    while i < len(text):
        matched = False
        for l in range(min(max_len, len(text) - i), 0, -1):
            cand = text[i:i + l]
            if cand in _token_set:
                tokens.append(cand)
                i += l
                matched = True
                break
        if not matched:
            i += 1
    return tokens


class VoiceSession:
    """
    单次录音会话管理类。
    用法：
    1. session = VoiceSession()
    2. session.start()  (在 pressed 事件中调用)
    3. ... 录音中 ...
    4. result = session.stop() (在 released 事件中调用，会阻塞直到处理完成)
    """
    def __init__(self):
        if not _load_model():
            raise RuntimeError("模型加载失败，无法开始录音")

        self.stream_obj = None
        self.audio_stream = None
        self.is_recording = False
        self._last_text = ""
        self._lock = threading.Lock()

        # 动态增益控制参数
        self.target_volume = 0.3
        self.min_gain = 1.0
        self.max_gain = 8.0
        self.smoothing_factor = 0.1
        self.current_gain = 1.0

    def _audio_callback(self, indata, frames, time_info, status):
        """内部音频回调 - 含动态增益"""
        with self._lock:
            if not self.is_recording:
                return

            samples = indata.flatten().astype(np.float32)

            # 动态增益计算 (AGC)
            rms = np.sqrt(np.mean(samples**2))

            if rms > 0.0001:
                ideal_gain = self.target_volume / rms
                clipped_gain = np.clip(ideal_gain, self.min_gain, self.max_gain)
                self.current_gain = self.current_gain * (1 - self.smoothing_factor) + clipped_gain * self.smoothing_factor
            else:
                self.current_gain = self.current_gain * (1 - self.smoothing_factor) + 1.0 * self.smoothing_factor

            samples = np.clip(samples * self.current_gain, -1.0, 1.0)

            # 送入模型
            self.stream_obj.accept_waveform(16000, samples)

            while _recognizer.is_ready(self.stream_obj):
                _recognizer.decode_stream(self.stream_obj)

            result = _recognizer.get_result(self.stream_obj)
            current_text = str(getattr(result, 'text', result)).strip()
            if current_text:
                self._last_text = current_text

    def start(self):
        """开始录音"""
        if self.is_recording:
            return

        self._last_text = ""
        self.current_gain = 1.0

        self.stream_obj = _recognizer.create_stream()
        self.is_recording = True

        self.audio_stream = sd.InputStream(
            channels=1,
            samplerate=16000,
            dtype='float32',
            callback=self._audio_callback
        )
        self.audio_stream.start()

    def stop(self):
        """
        停止录音并返回结果。
        返回: (原文字符串, 拼音字符串)
        """
        if not self.is_recording:
            return "", ""

        self.is_recording = False

        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None

        final_result = _recognizer.get_result(self.stream_obj)
        text = str(getattr(final_result, 'text', final_result)).strip()

        if not text:
            text = self._last_text

        tokens = _tokenize_text(text)
        pinyin_str = " ".join(tokens)

        self.stream_obj = None
        return text, pinyin_str


# ==========================================
# 给 UI 调用的便捷函数
# ==========================================

_current_session = None

def start_recording():
    """UI 按下时调用，开始录音"""
    global _current_session
    try:
        _current_session = VoiceSession()
        _current_session.start()
        return True
    except Exception:
        return False

def stop_and_get_result():
    """UI 松开时调用，停止录音并返回 (原文, 拼音)"""
    global _current_session
    if _current_session is None:
        return "", ""

    try:
        raw_text, pinyin = _current_session.stop()
        _current_session = None
        return raw_text, pinyin
    except Exception as e:
        _current_session = None
        return "错误", str(e)


if __name__ == "__main__":
    print("按回车开始录音，再按回车停止...")
    input()
    start_recording()
    print("录音中... (说话吧)")
    input()
    text, pinyin = stop_and_get_result()
    print(f"结果：{text}")
    print(f"拼音：{pinyin}")
