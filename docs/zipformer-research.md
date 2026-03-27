# Zipformer 模型调研报告

> 调研时间：2026-03-27 | 论文：ICLR 2024 Oral | 团队：小米新一代 Kaldi (k2-fsa)

---

## 一、模型概述

Zipformer 是新一代 Kaldi 团队（小米 Daniel Povey 团队）研发的语音识别编码器模型，发表于 **ICLR 2024**（获 Oral）。它是 **Conformer** 的下一代替代者，在**更快、更省内存、效果更好**三个维度同时超越了 Conformer。

**一句话总结**：用 Conformer **1/3 的计算量**，达到**更好的识别精度**。

---

## 二、核心架构创新

### 1. U-Net 式多分辨率编码器
传统 Conformer 以固定 25Hz 帧率处理整个序列。Zipformer 引入类似 U-Net 的结构：

```
50Hz → 25Hz → 12.5Hz → 6.25Hz → 12.5Hz → 25Hz
       ↓         ↓          ↓          ↑         ↑
     stack1    stack2     stack3     stack4    stack5
```

- 中间层大幅下采样（最低 6.25Hz），**显著减少 FLOPs**
- 后续上采样恢复分辨率，融合多尺度信息
- 不同 stack 使用不同嵌入维度（中间层更大）

### 2. 注意力权重复用
将 MHSA（多头自注意力）拆分为：
- **MHAW**：只计算注意力权重（计算一次）
- **SA**：汇聚信息（复用两次）
- **NLA**：非线性注意力（复用一次）

→ 一次注意力计算供 3 个模块使用，节省 ~50% 注意力计算量

### 3. BiasNorm（替代 LayerNorm）
- 引入可学习 bias，保留向量长度信息
- 使用 exp(γ) 作缩放因子，避免梯度翻转

### 4. Swoosh 激活函数（替代 Swish）
- SwooshR / SwooshL 两种变体
- 负数部分有非零斜率，避免"死神经元"

### 5. ScaledAdam 优化器
- 根据参数尺度缩放更新量
- 显式学习参数 scale
- 配合 Eden Schedule，减少对 warmup 和 batch size 的依赖

---

## 三、性能数据

### LibriSpeech（1000h 英文）

| 模型 | 参数量 | FLOPs | WER (clean) | WER (other) |
|------|--------|-------|-------------|-------------|
| Conformer-L (原文) | — | — | 2.1% | 4.3% |
| Conformer-L (复现) | — | 294.2 | 2.46% | 5.55% |
| **Zipformer-L** | 63.9M | **107.7** | **2.06%** | **4.63%** |
| **Zipformer-L*** (A100×8) | 63.9M | 107.7 | **2.00%** | **4.38%** |

→ **计算量降低 63%，精度相当甚至更好**

### Aishell-1（170h 中文）

| 模型 | 参数量 | CER |
|------|--------|-----|
| Conformer (ESPnet) | ~100M+ | 基线 |
| **Zipformer-S** | 8.4M | **优于 Conformer** |
| **Zipformer-M** | 32.4M | **SOTA** |
| **Zipformer-L** | 63.9M | **SOTA** |

### WenetSpeech（10000h+ 中文）

| 模型 | Test-Net | Test-Meeting |
|------|----------|-------------|
| Conformer (Wenet/ESPnet) | 基线 | 基线 |
| **Zipformer-S** | **优于两者** | **优于两者** |
| **Zipformer-M/L** | **全面 SOTA** | **全面 SOTA** |

→ Zipformer-S 参数量仅为 Conformer 的 **1/3**，效果更好

### 推理效率（V100 GPU, 30s 音频）

- 推理速度比同参数量 Conformer 快 **>50%**
- 峰值内存显著更低

---

## 四、与其他模型对比

### Zipformer vs Conformer

| 维度 | Conformer | Zipformer |
|------|-----------|-----------|
| 帧率 | 固定 25Hz | 多尺度 6.25~50Hz |
| 注意力 | 每层独立 MHSA | 权重复用，一次算三次用 |
| 计算量 | 基线 | 减少 50-63% |
| 精度 | 基线 | 相当或更好 |
| 推理速度 | 基线 | 快 50%+ |
| 训练收敛 | 需要仔细调参 | ScaledAdam 更稳定 |

### Zipformer vs Whisper

| 维度 | Whisper | Zipformer |
|------|---------|-----------|
| 定位 | 离线转录（encoder-decoder） | 流式识别（encoder-only + CTC/RNNT） |
| 模型大小 | tiny 39M → large 1550M | S 8.4M → L 63.9M |
| 延迟 | 高（需要完整语音段） | **极低（流式处理，160ms~320ms）** |
| 中文效果 | 中等（通用但不专精） | **优秀（WenetSpeech SOTA）** |
| KWS 支持 | ❌ 不支持关键词检测 | ✅ 原生 KWS 模型 |
| 端侧部署 | 困难（模型大、延迟高） | **友好（3.3M 模型即可工作）** |
| 开源生态 | OpenAI 维护 | k2-fsa/sherpa-onnx 完整工具链 |

---

## 五、sherpa-onnx KWS 模型现状

### 可用模型

| 模型 | 大小 | 语言 | 训练数据 | 发布时间 |
|------|------|------|---------|---------|
| **zh-en-3M-2025-12-20** | ~3M | 中英双语 | — | 2025.12 (最新) |
| wenetspeech-3.3M-2024-01-01 | 3.3M | 仅中文 | WenetSpeech 10000h | 2024.01 |
| gigaspeech-3.3M-2024-01-01 | 3.3M | 仅英文 | GigaSpeech 10000h | 2024.01 |

### 斩龙项目当前使用

- 模型：`wenetspeech epoch-12 chunk-16-left-64`（中文专用，WenetSpeech 训练）
- 已有 int8 量化版本
- 还存有 epoch-99 系列（未使用，建议删除节省空间）

### 升级建议

**推荐升级到 `zh-en-3M-2025-12-20`**：
1. 最新版本，可能融入了更多优化
2. 中英双语支持，兼容性更好
3. 支持不同 chunk size（8=160ms 低延迟 / 16=320ms 高精度）
4. 有 int8 量化版本

---

## 六、端侧部署生态

| 平台 | 方案 | 状态 |
|------|------|------|
| Windows/macOS/Linux | sherpa-onnx (ONNX Runtime) | ✅ 成熟 |
| Android/iOS | sherpa-onnx C API + JNI/ObjC | ✅ 成熟 |
| 高通骁龙 | Qualcomm AI Hub 优化版 | ✅ 官方支持 |
| 瑞芯微 RK3588 | RKNN 部署 | ✅ 社区验证 (RTF=0.22) |
| 浏览器 | sherpa-onnx WASM | ✅ 可用 |

---

## 七、结论与建议

### 对斩龙项目的评估

**Zipformer 非常适合斩龙的使用场景**，理由：

1. **超小模型可用** — 3.3M 参数的 KWS 模型就能工作，打包体积极小
2. **流式低延迟** — 160~320ms 延迟，适合实时语音指令
3. **中文 SOTA** — 在 WenetSpeech 10000h 数据集上效果最好
4. **原生 KWS** — 不像 Whisper 需要全文转录再匹配，Zipformer 有专用的关键词检测模式
5. **完整工具链** — sherpa-onnx 提供开箱即用的 Python API
6. **跨平台** — Windows/macOS/Linux 都有成熟方案

### 可以改进的方向

| 改进项 | 预期收益 | 难度 |
|--------|---------|------|
| 升级到 zh-en-3M-2025-12-20 | 更好的识别精度 | 低 |
| 删除 epoch-99 模型 | 减少 ~17MB 打包体积 | 低 |
| 尝试 chunk_size=8 | 延迟从 320ms 降到 160ms | 低 |
| 训练自定义 KWS 模型 | 针对游戏术语定制 | 高 |

### 与竞品的定位

- **需要离线全文转录** → 用 Whisper
- **需要实时关键词检测 + 超低延迟 + 小模型** → **用 Zipformer（当前选择✅）**
- **需要大规模通用 ASR** → 用 Conformer 或 Whisper large

**总结：Zipformer 是当前最适合斩龙的模型架构，没有需要换的理由，但可以升级到最新的模型版本。**
