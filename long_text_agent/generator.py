"""生成模块。

该模块负责根据规划生成长文本输出。
"""

from __future__ import annotations

from .llm_client import LlmClient
from .types import Plan


class TextGenerator:
    """文本生成器。

    参数:
        client: LLM客户端。
        enable_llm: 是否启用LLM生成。

    返回值:
        提供文本生成能力。

    关键实现细节:
        当前实现为占位式生成，强调可替换性与调试可控性。
    """

    def __init__(self, client: LlmClient, enable_llm: bool) -> None:
        """初始化生成器。

        参数:
            client: LLM客户端。
            enable_llm: 是否启用LLM生成。

        返回值:
            无。

        关键实现细节:
            当未启用LLM时保留占位式输出。
        """

        self._client: LlmClient = client
        self._enable_llm: bool = enable_llm

    def generate_text(self, instruction: str, plan: Plan) -> str:
        """根据规划生成长文本。

        参数:
            instruction: 任务指令。
            plan: 规划条目列表。

        返回值:
            生成的长文本。

        关键实现细节:
            以分段方式拼接输出，保证结构清晰。
        """

        if self._enable_llm:
            prompt: str = self._build_prompt(instruction, plan)
            return self._client.generate(prompt)

        sections: list[str] = []
        for item in plan:
            index_value: int = int(item["index"])
            summary_value: str = str(item["summary"])
            chunk_value: str = str(item["chunk"])
            sections.append(
                "【第" + str(index_value + 1) + "部分】\n" +
                "指令: " + instruction + "\n" +
                "摘要: " + summary_value + "\n" +
                "内容: " + chunk_value + "\n"
            )
        return "\n".join(sections)

    def _build_prompt(self, instruction: str, plan: Plan) -> str:
        """构建LLM提示词。

        参数:
            instruction: 任务指令。
            plan: 规划条目列表。

        返回值:
            用于LLM生成的提示词。

        关键实现细节:
            将规划条目作为结构化上下文拼接。
        """

        lines: list[str] = ["任务指令:", instruction, "", "规划:"]
        for item in plan:
            lines.append(
                "- index="
                + str(item["index"])
                + " summary="
                + str(item["summary"])
            )
        lines.append("")
        lines.append("请基于规划生成完整长文本。")
        return "\n".join(lines)
