"""困惑度配置模块。

该模块定义用于困惑度计算的配置结构。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerplexityConfig:
    """困惑度配置。

    参数:
        enable: 是否启用困惑度计算。
        endpoint: 困惑度计算API地址。
        text_field: 请求体中文本字段名。
        logprobs_field: 响应中对数概率列表字段名。

    返回值:
        不直接返回，作为配置对象供自检模块使用。

    关键实现细节:
        通过字段名适配不同API协议。
    """

    enable: bool
    endpoint: str
    text_field: str
    logprobs_field: str
