"""自检模块。

该模块负责对生成文本进行基础自检并产出指标。
"""

from __future__ import annotations

from .llm_client import LlmClient
from .perplexity import PerplexityConfig
from .types import Metrics


class SelfChecker:
    """自检器。

    参数:
        client: LLM客户端。
        perplexity_config: 困惑度配置。

    返回值:
        提供自检指标计算能力。

    关键实现细节:
        提供重复率与长度等基础指标，便于后续扩展。
    """

    def __init__(self, client: LlmClient, perplexity_config: PerplexityConfig) -> None:
        """初始化自检器。

        参数:
            client: LLM客户端。
            perplexity_config: 困惑度配置。

        返回值:
            无。

        关键实现细节:
            保留客户端与配置用于可选的困惑度计算。
        """

        self._client: LlmClient = client
        self._perplexity_config: PerplexityConfig = perplexity_config

    def self_check(self, output_text: str) -> Metrics:
        """对输出进行简单自检。

        参数:
            output_text: 生成文本。

        返回值:
            自检指标字典。

        关键实现细节:
            使用字符级去重比例作为基础重复度指标。
        """

        length_value: int = len(output_text)
        unique_chars: int = len(set(output_text))
        unique_ratio: float = 0.0
        if length_value > 0:
            unique_ratio = unique_chars / float(length_value)
        metrics: Metrics = {
            "length": length_value,
            "unique_ratio": unique_ratio,
            "self_check": "basic",
        }
        if self._perplexity_config.enable:
            perplexity_value: float = self._client.score_perplexity(
                endpoint=self._perplexity_config.endpoint,
                text_field=self._perplexity_config.text_field,
                logprobs_field=self._perplexity_config.logprobs_field,
                text=output_text,
            )
            metrics["perplexity"] = perplexity_value
        return metrics
