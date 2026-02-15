"""配置定义。

该模块定义长文本生成Agent的配置结构。
"""

from __future__ import annotations

from dataclasses import dataclass

from .ast_grep_splitter import AstGrepConfig
from .llm_client import LlmClientConfig
from .perplexity import PerplexityConfig
from .text_type import TextTypeConfig


@dataclass(frozen=True)
class AgentConfig:
    """Agent配置。

    参数:
        max_chunk_chars: 单块最大字符数。
        overlap_chars: 相邻块的重叠字符数。
        enable_overlap: 是否启用重叠策略。
        summary_chars: 规划阶段摘要长度。
        enable_self_check: 是否启用自检。
        ast_grep: AST-GREP语义拆分配置。
        text_type: 文本类型检测配置。
        llm_client: LLM客户端配置。
        perplexity: 困惑度配置。

    返回值:
        不直接返回，作为配置对象供Agent使用。

    关键实现细节:
        所有字段均为必填，避免默认值掩盖错误配置。
    """

    max_chunk_chars: int
    overlap_chars: int
    enable_overlap: bool
    summary_chars: int
    enable_self_check: bool
    ast_grep: AstGrepConfig
    text_type: TextTypeConfig
    llm_client: LlmClientConfig
    perplexity: PerplexityConfig
