# fuzzy_matcher.py — KWS 结果模糊匹配模块
# 当 KWS 返回的关键词带有变体后缀（_v1, _v2...）时，映射回原始技能名
# 同时提供编辑距离兜底匹配

import re
from difflib import SequenceMatcher


class FuzzyMatcher:
    """
    将 KWS 输出的关键词结果映射到实际的技能名。
    
    KWS 可能输出：
    - "踩"       → 精确匹配
    - "踩_v1"    → 方言变体，需要还原成 "踩"
    - "cai2"     → 什么都没匹配上，尝试模糊匹配
    """
    
    def __init__(self, macros_dict, fuzzy_threshold=0.65):
        """
        参数:
            macros_dict: dict — {技能名: 按键动作列表} 来自 ConfigManager
            fuzzy_threshold: float — 模糊匹配的最低相似度阈值 (0-1)
        """
        self._skill_names = set(macros_dict.keys())
        self._fuzzy_threshold = fuzzy_threshold
    
    def update(self, macros_dict):
        """配置变更时更新技能名列表"""
        self._skill_names = set(macros_dict.keys())
    
    def match(self, kws_result):
        """
        将 KWS 输出结果映射为技能名。
        
        参数:
            kws_result: str — KWS 返回的关键词字符串
        
        返回:
            str|None — 匹配到的技能名，未匹配返回 None
        """
        if not kws_result:
            return None
        
        result = kws_result.strip()
        
        # 1. 精确匹配
        if result in self._skill_names:
            return result
        
        # 2. 变体后缀还原：去掉 _v1, _v2, ... 后缀
        base_name = re.sub(r'_v\d+$', '', result)
        if base_name in self._skill_names:
            return base_name
        
        # 3. 去掉数字后缀的旧格式兼容：去掉 _1, _2, ... 后缀
        base_name_old = re.sub(r'_\d+$', '', result)
        if base_name_old in self._skill_names:
            return base_name_old
        
        # 4. 编辑距离模糊匹配（兜底）
        best_match = None
        best_score = 0
        
        for skill_name in self._skill_names:
            score = SequenceMatcher(None, result, skill_name).ratio()
            if score > best_score and score >= self._fuzzy_threshold:
                best_score = score
                best_match = skill_name
        
        return best_match
