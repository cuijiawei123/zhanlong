# voice_recorder.py (含动态自动增益修正版)

import sherpa_onnx
import sounddevice as sd
import numpy as np
import os
from pathlib import Path
import sys
import time
import threading

MODEL_DIR = "./model"
TOKENS_FILE = os.path.join(MODEL_DIR, "tokens.txt")

# 全局模型缓存
_recognizer = None
_token_set = None

def _load_model():
    """单例模式加载模型"""
    global _recognizer, _token_set
    if _recognizer is not None:
        return True
    
    if not os.path.exists(MODEL_DIR):
        # print(f"❌ 模型目录不存在：{MODEL_DIR}")
        return False

    files = [
        "encoder-epoch-12-avg-2-chunk-16-left-64.onnx",
        "decoder-epoch-12-avg-2-chunk-16-left-64.onnx",
        "joiner-epoch-12-avg-2-chunk-16-left-64.onnx",
        "tokens.txt"
    ]
    
    for f in files:
        if not os.path.exists(os.path.join(MODEL_DIR, f)):
            # print(f"❌ 缺失模型文件：{f}")
            return False

    # print("🔄 加载语音识别模型...")
    try:
        _recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            encoder=os.path.join(MODEL_DIR, "encoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
            decoder=os.path.join(MODEL_DIR, "decoder-epoch-12-avg-2-chunk-16-left-64.onnx"),
            joiner=os.path.join(MODEL_DIR, "joiner-epoch-12-avg-2-chunk-16-left-64.onnx"),
            tokens=TOKENS_FILE,
            sample_rate=16000,
            feature_dim=80,
            decoding_method="greedy_search",
            num_threads=2,
        )
        
        with open(TOKENS_FILE, encoding="utf-8") as f:
            _token_set = {line.split()[0] for line in f if line.strip()}
        
        # print("✅ 模型加载成功")
        return True
    except Exception as e:
        # print(f"❌ 模型加载失败：{e}")
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
        # 贪心匹配：从最长可能的 token 开始试
        for l in range(min(max_len, len(text) - i), 0, -1):
            cand = text[i:i + l]
            if cand in _token_set:
                tokens.append(cand)
                i += l
                matched = True
                break
        if not matched:
            # 如果单个字符都匹配不到，跳过该字符（避免死循环）
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

        # ✅ 新增：动态增益控制参数 (与 voice_listener.py 保持一致)
        self.target_volume = 0.3      # 目标音量幅度 (0.0~1.0)
        self.min_gain = 1.0           # 最小增益倍数
        self.max_gain = 8.0           # 最大增益倍数 (防止噪音爆炸)
        self.smoothing_factor = 0.1   # 平滑系数，防止增益突变
        self.current_gain = 1.0       # 当前实际使用的增益值

    def _audio_callback(self, indata, frames, time_info, status):
        """内部音频回调 - 已加入动态增益逻辑"""
        # if status:
        #     print(status, file=sys.stderr)
        
        with self._lock:
            if not self.is_recording:
                return

            # 1. 获取原始数据
            samples = indata.flatten().astype(np.float32)
            
            # 2. ✅ 核心：动态增益计算 (AGC)
            # 计算当前帧的能量 (RMS)
            rms = np.sqrt(np.mean(samples**2))
            
            # 动态调整增益
            if rms > 0.0001: 
                ideal_gain = self.target_volume / rms
                clipped_gain = np.clip(ideal_gain, self.min_gain, self.max_gain)
                
                # 平滑处理
                self.current_gain = self.current_gain * (1 - self.smoothing_factor) + clipped_gain * self.smoothing_factor
            else:
                # 静音时缓慢恢复增益到 1.0
                self.current_gain = self.current_gain * (1 - self.smoothing_factor) + 1.0 * self.smoothing_factor

            # 3. 应用增益
            samples = samples * self.current_gain
            
            # 4. 强制限幅 (Clipping)，防止爆音
            samples = np.clip(samples, -1.0, 1.0)

            # --- 原有逻辑：送入模型 ---
            self.stream_obj.accept_waveform(16000, samples)
            
            while _recognizer.is_ready(self.stream_obj):
                _recognizer.decode_stream(self.stream_obj)
            
            # 实时更新最后看到的文本
            result = _recognizer.get_result(self.stream_obj)
            current_text = str(getattr(result, 'text', result)).strip()
            if current_text:
                self._last_text = current_text

    def start(self):
        """开始录音"""
        if self.is_recording:
            return
        
        self._last_text = ""
        # 重置增益状态，避免上一次录音的增益残留影响
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
        # print("🎤 录音已开始...")

    def stop(self):
        """
        停止录音并返回结果。
        此函数会阻塞一小会儿以获取最终解码结果。
        返回: (原文字符串, 拼音字符串)
        """
        if not self.is_recording:
            return "", ""
        
        self.is_recording = False
        
        # 1. 停止音频流
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.audio_stream = None
        
        # 2. 强制获取最终结果
        final_result = _recognizer.get_result(self.stream_obj)
        text = str(getattr(final_result, 'text', final_result)).strip()
        
        # 如果 get_result 为空，用过程中记录的最后一个非空文本
        if not text:
            text = self._last_text
            
        # print(f"🛑 录音停止。识别结果：'{text}'")
        
        # 3. 转拼音
        tokens = _tokenize_text(text)
        pinyin_str = " ".join(tokens)
        
        # 清理
        self.stream_obj = None
        
        return text, pinyin_str

# ==========================================
# 🔥 给 UI 调用的便捷函数
# ==========================================

# 全局变量用于保存当前的 Session，防止被 GC 回收
_current_session = None

def start_recording():
    """
    UI 按下时调用。
    初始化并开始录音。
    """
    global _current_session
    try:
        _current_session = VoiceSession()
        _current_session.start()
        return True
    except Exception as e:
        # print(f"❌ 启动录音失败：{e}")
        return False

def stop_and_get_result():
    """
    UI 松开时调用。
    停止录音，处理数据，返回 (原文, 拼音)。
    如果没有正在进行的录音，返回 ("", "")
    """
    global _current_session
    if _current_session is None:
        return "", ""
    
    try:
        raw_text, pinyin = _current_session.stop()
        _current_session = None # 重置
        return raw_text, pinyin
    except Exception as e:
        # print(f"❌ 停止录音失败：{e}")
        _current_session = None
        return "错误", str(e)

if __name__ == "__main__":
    # 简单的命令行测试
    print("按回车开始录音，再按回车停止...")
    input()
    start_recording()
    print("录音中... (说话吧)")
    input()
    text, pinyin = stop_and_get_result()
    print(f"结果：{text}")
    print(f"拼音：{pinyin}")