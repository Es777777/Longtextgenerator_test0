"""统计模块。

该模块负责输出统计信息。
"""

from __future__ import annotations

from typing import List

from .types import Stats


class StatsBuilder:
    """统计构建器。

    参数:
        无。

    返回值:
        提供统计信息计算能力。

    关键实现细节:
        统计切块数量、平均块长度与输出长度。
    """

    def build_stats(self, chunks: List[str], output_text: str) -> Stats:
        """构建统计信息。

        参数:
            chunks: 切块列表。
            output_text: 输出文本。

        返回值:
            统计信息字典。

        关键实现细节:
            仅使用输入与输出长度进行统计，不引入隐式依赖。
        """

        chunk_count: int = len(chunks)
        average_chunk_length: float = 0.0
        if chunk_count > 0:
            total_length: int = sum(len(chunk) for chunk in chunks)
            average_chunk_length = total_length / float(chunk_count)
        return {
            "chunk_count": chunk_count,
            "average_chunk_length": average_chunk_length,
            "output_length": len(output_text),
        }
