"""文本类型检测配置。

该模块定义用于区分代码与自然语言文本的阈值配置。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextTypeConfig:
    """文本类型检测配置。

    参数:
        min_score: 判定为代码的最小评分阈值。
        line_ratio_divisor: 以行数缩放的阈值分母，分值需达到 max(min_score, 行数/line_ratio_divisor)。
        keyword_weight: 关键字命中权重。
        symbol_weight: 符号命中权重。
        line_weight: 行特征命中权重。
        keyword_pattern: 关键字匹配正则。
        symbol_pattern: 代码符号匹配正则。
        line_start_pattern: 行起始特征匹配正则。
        call_like_pattern: 类似函数声明的行模式正则。
        comment_pattern: 行注释模式正则。

    返回值:
        不直接返回，作为配置对象供检测逻辑使用。

    关键实现细节:
        通过阈值控制检测灵敏度，避免误判。
    """

    min_score: int
    line_ratio_divisor: int
    keyword_weight: int
    symbol_weight: int
    line_weight: int
    keyword_pattern: str
    symbol_pattern: str
    line_start_pattern: str
    call_like_pattern: str
    comment_pattern: str
