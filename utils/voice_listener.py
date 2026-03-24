# voice_listener.py（最终修正版 - 含动态自动增益）

import threading
import queue
import time
import pyautogui
import sounddevice as sd
import sherpa_onnx
import json
import numpy as np  # ✅ 新增：用于计算音频能量和数组操作

MODEL_DIR = "./model"
MIN_INTERVAL = 0.2
pyautogui.PAUSE = 0.1

def long_press(key, duration=0.5):
    pyautogui.keyDown(key)
    time.sleep(duration)
    pyautogui.keyUp(key)


class VoiceListener:
    def __init__(self, on_trigger=None, on_status=None):
        self.on_trigger = on_trigger or (lambda x: None)
        self.on_status = on_status or (lambda x: None)
        self.skill_queue = queue.Queue()
        self.executor_thread = None
        self.is_running = False
        self.kws = None
        self.stream = None
        self._last_trigger_time = 0
        self.INVOKER_MACROS = None

        # ✅ 新增：动态增益控制参数
        self.target_volume = 0.3      # 目标音量幅度 (0.0~1.0)，希望声音维持在这个水平
        self.min_gain = 1.0           # 最小增益倍数 (不缩小声音)
        self.max_gain = 15.0           # 最大增益倍数 (防止噪音爆炸，相当于系统音量拉满再放大)
        self.smoothing_factor = 0.1   # 平滑系数 (0.0-1.0)，越小增益变化越平滑，避免忽大忽小
        self.current_gain = 1.0       # 当前实际使用的增益值

    def start(self):
        with open('./utils/skills.json', 'r', encoding='utf-8') as f: 
            INVOKER_MACROS = json.load(f)
        self.INVOKER_MACROS = INVOKER_MACROS
        
        if self.is_running:
            return

        self.is_running = True
        try:
            self.on_status("starting")
            self.kws = sherpa_onnx.KeywordSpotter(
                encoder=f"{MODEL_DIR}/encoder-epoch-12-avg-2-chunk-16-left-64.onnx",
                decoder=f"{MODEL_DIR}/decoder-epoch-12-avg-2-chunk-16-left-64.onnx",
                joiner=f"{MODEL_DIR}/joiner-epoch-12-avg-2-chunk-16-left-64.onnx",
                tokens=f"{MODEL_DIR}/tokens.txt",
                keywords_file=f"{MODEL_DIR}/keywords_invoker.txt",
                num_threads=4,
                sample_rate=16000,
                feature_dim=80,
                max_active_paths=10,
            )
            self.stream = self.kws.create_stream()

            self.executor_thread = threading.Thread(target=self._execute_skills, daemon=True)
            self.executor_thread.start()

            self.on_status("listening")
    

            # 启动音频流
            with sd.InputStream(channels=1, samplerate=16000, dtype='float32', callback=self._audio_callback):
                while self.is_running:
                    time.sleep(0.01)

        except Exception as e:
            self.on_status(f"error: {str(e)}")
        finally:
            # 👇 关键：只在这里统一 emit stopped，不再调 stop()
            self.is_running = False
            self.on_status("stopped")  # ✅ 确保一定会通知 UI

    def _audio_callback(self, indata, frames, time_info, status):
        if not self.is_running or self.kws is None or self.stream is None:
            return

        # 1. 获取原始数据
        samples = indata.flatten().astype('float32')
        
        # 2. ✅ 核心：动态增益计算 (AGC)
        # 计算当前帧的能量 (RMS - 均方根)
        rms = np.sqrt(np.mean(samples**2))
        
        # 只有当有声音信号时才调整增益，避免除以0或纯静音时的剧烈波动
        if rms > 0.0001: 
            # 理想增益 = 目标音量 / 当前音量
            # 如果当前音量很小 (如0.05)，目标0.3，则理想增益 = 6.0
            ideal_gain = self.target_volume / rms
            
            # 限制增益范围 [min_gain, max_gain]
            clipped_gain = np.clip(ideal_gain, self.min_gain, self.max_gain)
            
            # 平滑处理：新增益 = 旧增益 * (1-因子) + 新计算增益 * 因子
            # 这样即使音量突变，增益也是渐进变化的，听感更自然
            self.current_gain = self.current_gain * (1 - self.smoothing_factor) + clipped_gain * self.smoothing_factor
        else:
            # 如果是纯静音，让增益缓慢回落到 1.0，避免底噪被无限放大
            self.current_gain = self.current_gain * (1 - self.smoothing_factor) + 1.0 * self.smoothing_factor

        # 3. 应用增益
        samples = samples * self.current_gain
        
        # 4. 强制限幅 (Clipping)，防止超过 -1.0 ~ 1.0 导致爆音/失真
        samples = np.clip(samples, -1.0, 1.0)

        # --- 下面是原有的识别逻辑 ---
        self.stream.accept_waveform(16000, samples)

        while self.kws.is_ready(self.stream):
            self.kws.decode_stream(self.stream)

        result = self.kws.get_result(self.stream)
        current_time = time.time()

        if result and (current_time - self._last_trigger_time) >= MIN_INTERVAL:
            self._last_trigger_time = current_time
     
            self.skill_queue.put(result)
            self.on_trigger(result)

    def _execute_skills(self):
        while self.is_running:
            try:
                skill_name = self.skill_queue.get(timeout=0.1)
                if skill_name in self.INVOKER_MACROS:
                    
                    for action in self.INVOKER_MACROS[skill_name]:

                        if isinstance(action, list):
                            first_elem = action[0]
                            
                            # 1. 处理特殊指令：双击
                            if first_elem == "double_click":
                                
                                key = action[1]
                                pyautogui.press(key)
                                time.sleep(0.05)
                                pyautogui.keyDown(key)
                                time.sleep(0.05)
                                pyautogui.keyUp(key)
                            
                            # 2. 处理普通组合键 (如 ('ctrl', 'c') 或 ('shift', 'a'))
                            else:
                        
                                # 🔥 优化逻辑：手动模拟标准的组合键过程
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
                   
                            # 3. 处理单个按键 (字符串)
                            pyautogui.press(str(action))
                        
                self.skill_queue.task_done()
            except queue.Empty:
                continue
    
    def stop(self):
        """外部调用此方法即可安全停止监听"""
        self.is_running = False