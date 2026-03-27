# dialect_variants.py — 方言变体自动生成引擎
# 根据常见方言混淆规则，自动为每个关键词生成发音变体

import re
import itertools


# ==========================================
# 常见方言混淆规则
# 每条规则：原始拼音部分 → 可能的方言替代
# ==========================================

# 声母混淆规则
INITIAL_CONFUSIONS = {
    'zh': ['z'],       # 平翘舌不分
    'z': ['zh'],
    'ch': ['c'],
    'c': ['ch'],
    'sh': ['s'],
    's': ['sh'],
    'l': ['n'],        # l/n 不分（湖南、江西、四川）
    'n': ['l'],
    'h': ['f'],        # h/f 不分（湖南）
    'f': ['h'],
    'r': ['l'],        # r/l 不分（南方多地）
}

# 韵母/声调混淆规则
# 前后鼻音不分（华中、华南大面积分布）
FINAL_CONFUSIONS = {
    # -n / -ng 混淆
    'ēn': ['ēng'], 'ēng': ['ēn'],
    'én': ['éng'], 'éng': ['én'],
    'ěn': ['ěng'], 'ěng': ['ěn'],
    'èn': ['èng'], 'èng': ['èn'],
    'īn': ['īng'], 'īng': ['īn'],
    'ín': ['íng'], 'íng': ['ín'],
    'ǐn': ['ǐng'], 'ǐng': ['ǐn'],
    'ìn': ['ìng'], 'ìng': ['ìn'],
    'ān': ['āng'], 'āng': ['ān'],
    'án': ['áng'], 'áng': ['án'],
    'ǎn': ['ǎng'], 'ǎng': ['ǎn'],
    'àn': ['àng'], 'àng': ['àn'],
    'ūn': ['ōng'], 'ōng': ['ūn'],
    'ún': ['óng'], 'óng': ['ún'],
    'ǔn': ['ǒng'], 'ǒng': ['ǔn'],
    'ùn': ['òng'], 'òng': ['ùn'],
    # iān/iāng 混淆
    'iān': ['iāng'], 'iāng': ['iān'],
    'ián': ['iáng'], 'iáng': ['ián'],
    'iǎn': ['iǎng'], 'iǎng': ['iǎn'],
    'iàn': ['iàng'], 'iàng': ['iàn'],
}

# 声调混淆（用于单字关键词，发音不准时声调偏移）
# 给定一个带声调的韵母，返回其他声调变体
_TONE_MARKS = {
    'a': 'āáǎà', 'e': 'ēéěè', 'i': 'īíǐì',
    'o': 'ōóǒò', 'u': 'ūúǔù', 'ü': 'ǖǘǚǜ',
}

# 反向映射：声调字符 → (基础字符, 声调序号)
_TONE_REVERSE = {}
for base, tones in _TONE_MARKS.items():
    for idx, tone_char in enumerate(tones):
        _TONE_REVERSE[tone_char] = (base, idx)


def _get_tone_variants(token):
    """
    给定一个拼音 token（如 'ái'），返回其他声调变体（如 ['āi', 'ǎi', 'ài']）
    """
    variants = []
    for i, ch in enumerate(token):
        if ch in _TONE_REVERSE:
            base, current_tone = _TONE_REVERSE[ch]
            tones = _TONE_MARKS[base]
            for j, tone_char in enumerate(tones):
                if j != current_tone:
                    variant = token[:i] + tone_char + token[i+1:]
                    variants.append(variant)
            break  # 一个 token 里只有一个声调标记
    return variants


def generate_variants(pinyin_tokens, max_variants=5, enable_tone_variants=True):
    """
    给定一个关键词的拼音 token 列表，生成方言变体。
    
    参数:
        pinyin_tokens: list[str] — 拼音 token 列表，如 ['f', 'ù', 'zh', 'ì']
        max_variants: int — 最多生成多少个变体
        enable_tone_variants: bool — 是否生成声调变体（对单字词推荐开启）
    
    返回:
        list[list[str]] — 变体 token 列表的列表
    """
    if not pinyin_tokens:
        return []

    # 为每个 token 位置生成候选集
    # candidates[i] = [原始token, 变体1, 变体2, ...]
    candidates = []

    for token in pinyin_tokens:
        token_options = [token]  # 原始值始终保留

        # 声母混淆
        if token in INITIAL_CONFUSIONS:
            token_options.extend(INITIAL_CONFUSIONS[token])

        # 韵母/鼻音混淆
        if token in FINAL_CONFUSIONS:
            token_options.extend(FINAL_CONFUSIONS[token])

        # 声调变体
        if enable_tone_variants:
            tone_vars = _get_tone_variants(token)
            token_options.extend(tone_vars)

        # 去重但保持顺序
        seen = set()
        unique_options = []
        for opt in token_options:
            if opt not in seen:
                seen.add(opt)
                unique_options.append(opt)

        candidates.append(unique_options)

    # 生成组合（笛卡尔积），但排除原始组合
    original = tuple(pinyin_tokens)
    variants = []

    # 策略：不做全笛卡尔积（太多了），而是每次只替换一个位置
    for pos in range(len(candidates)):
        for alt_token in candidates[pos][1:]:  # 跳过第一个（原始值）
            variant = list(pinyin_tokens)
            variant[pos] = alt_token
            if tuple(variant) != original:
                variants.append(variant)

    # 去重
    seen_variants = set()
    unique_variants = []
    for v in variants:
        key = tuple(v)
        if key not in seen_variants:
            seen_variants.add(key)
            unique_variants.append(v)

    # 限制数量
    return unique_variants[:max_variants]


def generate_keywords_with_variants(name, pinyin_str, max_variants=5, enable_tone_variants=None):
    """
    为一个关键词生成完整的 keywords_invoker.txt 行（含原始 + 变体）。
    
    参数:
        name: str — 关键词名称，如 "踩"
        pinyin_str: str — 拼音字符串，如 "c ái"
        max_variants: int — 最多生成多少个变体
        enable_tone_variants: bool|None — 是否开启声调变体。None=自动（单字开，多字关）
    
    返回:
        list[str] — keywords_invoker.txt 的行列表
    """
    tokens = pinyin_str.strip().split()
    if not tokens:
        return []

    # 自动判断是否开启声调变体：单字/双字词开启，多字词关闭（避免变体爆炸）
    if enable_tone_variants is None:
        # 估算音节数（声母不算音节，只有韵母算）
        # 简单策略：token 数 <= 4 的认为是短词，开启声调变体
        enable_tone_variants = len(tokens) <= 4

    # 根据关键词长度设置阈值：短词严格，长词宽松
    if len(tokens) <= 2:
        threshold = " :0.35"   # 单字，高阈值减少误触
    elif len(tokens) <= 4:
        threshold = " :0.25"   # 双字，中等阈值
    else:
        threshold = " :0.15"   # 多字，低阈值
    
    lines = []

    # 原始行
    lines.append(f"{pinyin_str} @{name}{threshold}")

    # 变体行
    variants = generate_variants(tokens, max_variants=max_variants, enable_tone_variants=enable_tone_variants)
    for i, variant_tokens in enumerate(variants):
        variant_pinyin = " ".join(variant_tokens)
        # 变体的阈值比原始高一点（更严格），减少误触
        variant_threshold = " :0.40" if len(tokens) <= 2 else " :0.30"
        lines.append(f"{variant_pinyin} @{name}_v{i+1}{variant_threshold}")

    return lines


def generate_full_keywords_file(voice_keywords):
    """
    从 voice_keywords 字典生成完整的 keywords_invoker.txt 内容。
    
    参数:
        voice_keywords: dict — {name: pinyin_str}
    
    返回:
        str — 完整的文件内容
    """
    all_lines = []
    for name, pinyin_str in voice_keywords.items():
        if pinyin_str:
            keyword_lines = generate_keywords_with_variants(name, pinyin_str)
            all_lines.extend(keyword_lines)

    return "\n".join(all_lines) + "\n" if all_lines else ""
