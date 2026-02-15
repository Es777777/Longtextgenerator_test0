"""规划模块。

该模块负责将切块内容转为可执行的基础规划。
"""

from __future__ import annotations

from typing import List

from .config import AgentConfig
from .types import Plan, PlanItem


class PlanBuilder:
    """规划构建器。

    参数:
        config: AgentConfig 配置对象。

    返回值:
        提供规划构建能力。

    关键实现细节:
        以摘要作为最小规划单元，便于后续替换为更复杂策略。
    """

    def __init__(self, config: AgentConfig) -> None:
        """初始化规划构建器。

        参数:
            config: AgentConfig 配置对象。

        返回值:
            无。

        关键实现细节:
            保存配置以控制摘要长度。
        """

        self._config: AgentConfig = config

    def build_plan(self, instruction: str, chunks: List[str]) -> Plan:
        """构建基础规划。

        参数:
            instruction: 任务指令。
            chunks: 切块后的文本列表。

        返回值:
            规划条目列表，每条包含索引、摘要与原始块内容。

        关键实现细节:
            通过截断摘要实现最小规划占位。
        """

        plan: Plan = []
        for index, chunk in enumerate(chunks):
            summary: str = chunk[: self._config.summary_chars]
            item: PlanItem = {
                "index": index,
                "summary": summary,
                "chunk": chunk,
                "instruction": instruction,
            }
            plan.append(item)
        return plan
