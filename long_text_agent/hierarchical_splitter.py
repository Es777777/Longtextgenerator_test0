"""层次化语义拆分模块。

该模块提供面向自然语言文本的层次拆分策略，优先识别标题结构，
在缺少标题时按段落进行拆分。
"""

from __future__ import annotations

import re
from typing import List


class HierarchicalSplitter:
    """层次化语义拆分器。

    参数:
        无。

    返回值:
        提供自然语言文本的结构化切块能力。

    关键实现细节:
        优先使用标题作为章节边界，若无标题则按段落边界拆分。
    """

    def split(self, text: str) -> List[str]:
        """对自然语言文本进行层次化拆分。

        参数:
            text: 待拆分文本。

        返回值:
            切块后的文本列表。

        关键实现细节:
            当检测到标题时使用标题分段，否则使用段落分段。
        """

        lines: List[str] = text.splitlines()
        has_heading: bool = any(self._is_heading(line) for line in lines)
        if has_heading:
            return self._split_by_heading(lines)
        return self._split_by_paragraph(text)

    def _split_by_heading(self, lines: List[str]) -> List[str]:
        """按标题进行分段。

        参数:
            lines: 文本行列表。

        返回值:
            章节级切块列表。

        关键实现细节:
            标题作为新段落起点，后续内容并入直到下一个标题。
        """

        sections: List[str] = []
        buffer_lines: List[str] = []
        for line in lines:
            if self._is_heading(line):
                if len(buffer_lines) > 0:
                    sections.append("\n".join(buffer_lines).strip())
                    buffer_lines = []
                buffer_lines.append(line.rstrip())
                continue
            buffer_lines.append(line.rstrip())
        if len(buffer_lines) > 0:
            sections.append("\n".join(buffer_lines).strip())
        return [section for section in sections if section != ""]

    def _split_by_paragraph(self, text: str) -> List[str]:
        """按段落进行分段。

        参数:
            text: 输入文本。

        返回值:
            段落级切块列表。

        关键实现细节:
            以空行作为段落边界，保留原始内容顺序。
        """

        paragraphs: List[str] = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", text)
        ]
        return [paragraph for paragraph in paragraphs if paragraph != ""]

    def _is_heading(self, line: str) -> bool:
        """判断是否为标题行。

        参数:
            line: 单行文本。

        返回值:
            是否为标题。

        关键实现细节:
            支持Markdown标题与常见中文层级标题格式。
        """

        stripped: str = line.strip()
        if stripped == "":
            return False
        if re.match(r"^#{1,6}\s+", stripped) is not None:
            return True
        if re.match(r"^第[一二三四五六七八九十0-9]+[章节篇]", stripped) is not None:
            return True
        if re.match(r"^[一二三四五六七八九十0-9]+[、.．]\s*", stripped) is not None:
            return True
        if re.match(r"^（[一二三四五六七八九十0-9]+）", stripped) is not None:
            return True
        return False
