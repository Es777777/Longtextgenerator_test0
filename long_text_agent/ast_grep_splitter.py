"""AST-GREP语义拆分模块。

该模块通过调用AST-GREP命令行工具，实现基于语法树的语义切块。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import subprocess
import tempfile
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class AstGrepConfig:
    """AST-GREP配置。

    参数:
        enable: 是否启用AST-GREP语义拆分。
        command: AST-GREP命令行入口（例如sg）。
        language: 代码语言标识（例如python、javascript）。
        patterns: 用于匹配语法节点的模式列表。

    返回值:
        不直接返回，作为配置对象供拆分器使用。

    关键实现细节:
        patterns必须非空，否则无法构建语义拆分范围。
    """

    enable: bool
    command: str
    language: str
    patterns: List[str]


class AstGrepSplitter:
    """AST-GREP语义拆分器。

    参数:
        config: AstGrepConfig 配置对象。

    返回值:
        提供语义切块能力。

    关键实现细节:
        通过AST-GREP返回的范围信息切分文本，避免纯字符切块破坏结构。
    """

    def __init__(self, config: AstGrepConfig) -> None:
        """初始化拆分器。

        参数:
            config: AstGrepConfig 配置对象。

        返回值:
            无。

        关键实现细节:
            仅保存配置，不在初始化阶段执行外部命令。
        """

        self._config: AstGrepConfig = config

    def split(self, text: str) -> List[str]:
        """基于AST-GREP进行语义拆分。

        参数:
            text: 待拆分文本。

        返回值:
            语义切块列表。

        关键实现细节:
            对多模式结果进行合并排序，并依据范围切分原始文本。
        """

        matches: List[Tuple[int, int]] = self._collect_matches(text)
        if len(matches) == 0:
            return []
        merged: List[Tuple[int, int]] = self._merge_ranges(matches)
        return [text[start:end] for start, end in merged if end > start]

    def _collect_matches(self, text: str) -> List[Tuple[int, int]]:
        """收集AST-GREP匹配范围。

        参数:
            text: 待拆分文本。

        返回值:
            匹配范围列表，使用字符索引区间表示。

        关键实现细节:
            每个pattern独立执行，结果汇总后统一排序。
        """

        offsets: List[int] = self._build_line_offsets(text)
        matches: List[Tuple[int, int]] = []
        for pattern in self._config.patterns:
            data: Dict[str, object] = self._run_ast_grep(pattern, text)
            raw_matches: List[Dict[str, object]] = list(data.get("matches", []))
            for item in raw_matches:
                range_data: Dict[str, object] = dict(item.get("range", {}))
                start_data: Dict[str, object] = dict(range_data.get("start", {}))
                end_data: Dict[str, object] = dict(range_data.get("end", {}))
                start_index: int = self._to_index(offsets, start_data)
                end_index: int = self._to_index(offsets, end_data)
                if end_index > start_index:
                    matches.append((start_index, end_index))
        return matches

    def _run_ast_grep(self, pattern: str, text: str) -> Dict[str, object]:
        """执行AST-GREP命令并返回JSON结果。

        参数:
            pattern: AST-GREP匹配模式。
            text: 待拆分文本。

        返回值:
            AST-GREP返回的JSON数据。

        关键实现细节:
            使用临时文件作为输入，确保命令行工具兼容。
        """

        temp_path: str = ""
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as temp_file:
                temp_file.write(text)
                temp_path = temp_file.name

            command: List[str] = [
                self._config.command,
                "--json",
                "-p",
                pattern,
                "--lang",
                self._config.language,
                temp_path,
            ]
            result: subprocess.CompletedProcess[str] = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError("AST-GREP执行失败: " + result.stderr.strip())
            return json.loads(result.stdout)
        except FileNotFoundError as exc:
            raise RuntimeError("未找到AST-GREP命令: " + self._config.command) from exc
        finally:
            if temp_path != "":
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def _build_line_offsets(self, text: str) -> List[int]:
        """构建行起始偏移。

        参数:
            text: 输入文本。

        返回值:
            每行起始字符索引列表。

        关键实现细节:
            保留换行符长度，确保行列转字符索引准确。
        """

        offsets: List[int] = []
        current_index: int = 0
        for line in text.splitlines(keepends=True):
            offsets.append(current_index)
            current_index += len(line)
        if text.endswith("\n") is False:
            offsets.append(current_index)
        return offsets

    def _to_index(self, offsets: List[int], location: Dict[str, object]) -> int:
        """将行列转换为字符索引。

        参数:
            offsets: 行起始偏移列表。
            location: 包含line与column的位置信息。

        返回值:
            字符索引。

        关键实现细节:
            行号默认按1基，列号按0基处理。
        """

        line_value: int = int(location.get("line", 1))
        column_value: int = int(location.get("column", 0))
        line_index: int = max(line_value - 1, 0)
        if line_index >= len(offsets):
            return len(offsets)
        return offsets[line_index] + column_value

    def _merge_ranges(self, ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """合并重叠范围。

        参数:
            ranges: 范围列表。

        返回值:
            合并后的范围列表。

        关键实现细节:
            按起始位置排序后线性合并。
        """

        sorted_ranges: List[Tuple[int, int]] = sorted(ranges, key=lambda item: item[0])
        merged: List[Tuple[int, int]] = []
        for start, end in sorted_ranges:
            if len(merged) == 0:
                merged.append((start, end))
                continue
            last_start, last_end = merged[-1]
            if start <= last_end:
                merged[-1] = (last_start, max(last_end, end))
            else:
                merged.append((start, end))
        return merged
