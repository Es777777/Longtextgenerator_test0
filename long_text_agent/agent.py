"""Agent核心模块。

该模块负责组织拆分、规划、生成与自检流程。
"""

from __future__ import annotations

from typing import Dict

from .checker import SelfChecker
from .config import AgentConfig
from .generator import TextGenerator
from .llm_client import LlmClient
from .planner import PlanBuilder
from .segmenter import TextSegmenter
from .stats import StatsBuilder
from .types import Diagnostics, Metrics, Plan, Stats


class LongTextAgent:
    """长文本生成基础Agent。

    参数:
        config: AgentConfig 配置对象。

    返回值:
        该类用于生成长文本输出与诊断信息。

    关键实现细节:
        采用“拆分-规划-生成-自检”的阶段化流程，便于后续替换子策略。
    """

    def __init__(self, config: AgentConfig) -> None:
        """初始化Agent。

        参数:
            config: AgentConfig 配置对象。

        返回值:
            无。

        关键实现细节:
            初始化时进行配置校验，避免运行时隐藏错误。
        """

        self._validate_config(config)
        self._config: AgentConfig = config
        self._segmenter: TextSegmenter = TextSegmenter(config)
        self._planner: PlanBuilder = PlanBuilder(config)
        self._llm_client: LlmClient = LlmClient(config.llm_client)
        self._generator: TextGenerator = TextGenerator(self._llm_client, config.llm_client.enable)
        self._checker: SelfChecker = SelfChecker(self._llm_client, config.perplexity)
        self._stats_builder: StatsBuilder = StatsBuilder()

    def run(self, instruction: str, context_text: str, return_diagnostics: bool) -> Diagnostics:
        """执行长文本生成流程。

        参数:
            instruction: 任务指令。
            context_text: 输入上下文文本。
            return_diagnostics: 是否返回诊断信息。

        返回值:
            包含输出文本，必要时附带损失、指标与统计信息的字典。

        关键实现细节:
            输出遵循阶段化流程，并在必要时附带自检指标。
        """

        self._validate_inputs(instruction, context_text)

        # 第一阶段：语义拆分
        chunks: list[str] = self._segmenter.segment_text(context_text)

        # 第二阶段：结构规划
        plan: Plan = self._planner.build_plan(instruction, chunks)

        # 第三阶段：生成输出
        output_text: str = self._generator.generate_text(instruction, plan)

        # 第四阶段：自检与诊断
        metrics: Metrics = {}
        stats: Stats = {}
        if self._config.enable_self_check:
            metrics = self._checker.self_check(output_text)
        stats = self._stats_builder.build_stats(chunks, output_text)

        if return_diagnostics:
            return {
                "output": output_text,
                "loss": None,
                "metrics": metrics,
                "stats": stats,
                "plan": plan,
            }

        return {"output": output_text}

    def _validate_config(self, config: AgentConfig) -> None:
        """校验配置有效性。

        参数:
            config: AgentConfig 配置对象。

        返回值:
            无。

        关键实现细节:
            关键维度必须满足正数与边界约束，避免分块策略失效。
        """

        if config.max_chunk_chars <= 0:
            raise ValueError("max_chunk_chars必须为正数")
        if config.overlap_chars < 0:
            raise ValueError("overlap_chars不能为负数")
        if config.overlap_chars >= config.max_chunk_chars:
            raise ValueError("overlap_chars必须小于max_chunk_chars")
        if config.summary_chars <= 0:
            raise ValueError("summary_chars必须为正数")
        if config.ast_grep.enable:
            if config.ast_grep.command.strip() == "":
                raise ValueError("ast_grep.command不能为空")
            if config.ast_grep.language.strip() == "":
                raise ValueError("ast_grep.language不能为空")
            if len(config.ast_grep.patterns) == 0:
                raise ValueError("ast_grep.patterns不能为空")
        if config.text_type.min_score <= 0:
            raise ValueError("text_type.min_score必须为正数")
        if config.text_type.line_ratio_divisor <= 0:
            raise ValueError("text_type.line_ratio_divisor必须为正数")
        if config.text_type.keyword_weight <= 0:
            raise ValueError("text_type.keyword_weight必须为正数")
        if config.text_type.symbol_weight <= 0:
            raise ValueError("text_type.symbol_weight必须为正数")
        if config.text_type.line_weight <= 0:
            raise ValueError("text_type.line_weight必须为正数")
        if config.text_type.keyword_pattern.strip() == "":
            raise ValueError("text_type.keyword_pattern不能为空")
        if config.text_type.symbol_pattern.strip() == "":
            raise ValueError("text_type.symbol_pattern不能为空")
        if config.text_type.line_start_pattern.strip() == "":
            raise ValueError("text_type.line_start_pattern不能为空")
        if config.text_type.call_like_pattern.strip() == "":
            raise ValueError("text_type.call_like_pattern不能为空")
        if config.text_type.comment_pattern.strip() == "":
            raise ValueError("text_type.comment_pattern不能为空")
        if config.llm_client.enable:
            if config.llm_client.base_url.strip() == "":
                raise ValueError("llm_client.base_url不能为空")
            if config.llm_client.api_key_env.strip() == "":
                raise ValueError("llm_client.api_key_env不能为空")
            if config.llm_client.model.strip() == "":
                raise ValueError("llm_client.model不能为空")
            if config.llm_client.timeout_seconds <= 0:
                raise ValueError("llm_client.timeout_seconds必须为正数")
            if config.llm_client.max_retries < 0:
                raise ValueError("llm_client.max_retries不能为负数")
        if config.perplexity.enable:
            if config.perplexity.endpoint.strip() == "":
                raise ValueError("perplexity.endpoint不能为空")
            if config.perplexity.text_field.strip() == "":
                raise ValueError("perplexity.text_field不能为空")
            if config.perplexity.logprobs_field.strip() == "":
                raise ValueError("perplexity.logprobs_field不能为空")

    def _validate_inputs(self, instruction: str, context_text: str) -> None:
        """校验输入有效性。

        参数:
            instruction: 任务指令。
            context_text: 输入上下文文本。

        返回值:
            无。

        关键实现细节:
            避免空指令或空上下文导致流程失真。
        """

        if instruction.strip() == "":
            raise ValueError("instruction不能为空")
        if context_text.strip() == "":
            raise ValueError("context_text不能为空")
