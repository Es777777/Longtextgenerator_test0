"""文本拆分模块。

该模块负责对输入文本进行语义拆分与分块。
"""

from __future__ import annotations

import re
from typing import List

from .ast_grep_splitter import AstGrepSplitter
from .hierarchical_splitter import HierarchicalSplitter

from .config import AgentConfig


class TextSegmenter:
    """文本拆分器。

    参数:
        config: AgentConfig 配置对象。

    返回值:
        提供文本拆分能力。

    关键实现细节:
        采用“分句-合并-重叠”的阶段化处理方式。
    """

    def __init__(self, config: AgentConfig) -> None:
        """初始化拆分器。

        参数:
            config: AgentConfig 配置对象。

        返回值:
            无。

        关键实现细节:
            保留配置对象供后续拆分流程使用。
        """

        self._config: AgentConfig = config
        self._ast_grep_splitter: AstGrepSplitter | None = None
        if self._config.ast_grep.enable:
            self._ast_grep_splitter = AstGrepSplitter(self._config.ast_grep)
        self._hierarchical_splitter: HierarchicalSplitter = HierarchicalSplitter()

    def segment_text(self, text: str) -> List[str]:
        """将输入文本进行语义拆分并切块。

        参数:
            text: 待拆分的文本。

        返回值:
            切块后的文本列表。

        关键实现细节:
            先基于中英文句号类符号进行粗分句，再按最大长度拼接成块。
        """

        # 第一阶段：文本类型识别
        if self._is_probably_code(text):
            # 第二阶段：语义拆分（AST-GREP优先）
            if self._ast_grep_splitter is not None:
                semantic_chunks: List[str] = self._ast_grep_splitter.split(text)
                if len(semantic_chunks) > 0:
                    return self._post_process_chunks(semantic_chunks)
            sentences: List[str] = self._split_sentences(text)
        else:
            # 第二阶段：自然语言层次拆分
            semantic_chunks = self._hierarchical_splitter.split(text)
            if len(semantic_chunks) > 0:
                return self._post_process_chunks(semantic_chunks)
            sentences = self._split_sentences(text)

        # 第一阶段：句子合并成块
        chunks: List[str] = []
        current_chunk: str = ""
        for sentence in sentences:
            if len(sentence) > self._config.max_chunk_chars:
                # 第二阶段：过长句子切分
                split_parts: List[str] = self._split_long_sentence(sentence)
                for part in split_parts:
                    if current_chunk == "":
                        current_chunk = part
                    elif len(current_chunk) + len(part) <= self._config.max_chunk_chars:
                        current_chunk = current_chunk + part
                    else:
                        chunks.append(current_chunk)
                        current_chunk = part
                continue

            if current_chunk == "":
                current_chunk = sentence
                continue

            if len(current_chunk) + len(sentence) <= self._config.max_chunk_chars:
                current_chunk = current_chunk + sentence
            else:
                chunks.append(current_chunk)
                current_chunk = sentence

        if current_chunk != "":
            chunks.append(current_chunk)

        return self._post_process_chunks(chunks)

    def _is_probably_code(self, text: str) -> bool:
        """判断文本是否可能为代码。

        参数:
            text: 输入文本。

        返回值:
            是否为代码文本。

        关键实现细节:
            通过关键字、符号密度与行特征综合打分。
        """

        lines: List[str] = text.splitlines()
        if len(lines) == 0:
            return False

        keyword_pattern: str = self._config.text_type.keyword_pattern
        symbol_pattern: str = self._config.text_type.symbol_pattern
        line_start_pattern: str = self._config.text_type.line_start_pattern
        call_like_pattern: str = self._config.text_type.call_like_pattern
        comment_pattern: str = self._config.text_type.comment_pattern

        keyword_hits: int = len(re.findall(keyword_pattern, text))
        symbol_hits: int = len(re.findall(symbol_pattern, text))
        code_like_lines: int = 0
        for line in lines:
            stripped: str = line.strip()
            if stripped == "":
                continue
            if re.match(line_start_pattern, stripped) is not None:
                code_like_lines += 1
            if re.match(call_like_pattern, stripped) is not None:
                code_like_lines += 1
            if re.match(comment_pattern, stripped) is not None:
                code_like_lines += 1

        score: int = (
            keyword_hits * self._config.text_type.keyword_weight
            + symbol_hits * self._config.text_type.symbol_weight
            + code_like_lines * self._config.text_type.line_weight
        )
        ratio_divisor: int = max(1, self._config.text_type.line_ratio_divisor)
        threshold: int = max(self._config.text_type.min_score, len(lines) // ratio_divisor)
        return score >= threshold

    def _post_process_chunks(self, chunks: List[str]) -> List[str]:
        """对切块结果进行后处理。

        参数:
            chunks: 原始切块列表。

        返回值:
            处理后的切块列表。

        关键实现细节:
            先对超长块进行切分，再根据配置决定是否加入重叠内容。
        """

        processed: List[str] = []
        for chunk in chunks:
            if len(chunk) <= self._config.max_chunk_chars:
                processed.append(chunk)
                continue
            split_parts: List[str] = self._split_long_sentence(chunk)
            processed.extend(split_parts)

        if self._config.enable_overlap and self._config.overlap_chars > 0:
            processed = self._apply_overlap(processed)

        return processed

    def _split_sentences(self, text: str) -> List[str]:
        """基于标点进行分句。

        参数:
            text: 输入文本。

        返回值:
            句子列表。

        关键实现细节:
            保留标点以维持语义完整性。
        """

        pattern: str = r"([。！？.!?])"
        parts: List[str] = re.split(pattern, text)
        sentences: List[str] = []
        buffer_text: str = ""
        for part in parts:
            if part == "":
                continue
            if re.match(pattern, part) is not None:
                buffer_text = buffer_text + part
                sentences.append(buffer_text)
                buffer_text = ""
            else:
                if buffer_text == "":
                    buffer_text = part
                else:
                    buffer_text = buffer_text + part
        if buffer_text != "":
            sentences.append(buffer_text)
        return sentences

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """切分超长句子。

        参数:
            sentence: 单个句子文本。

        返回值:
            切分后的句子片段列表。

        关键实现细节:
            使用固定长度切分，保证不会超过块长度上限。
        """

        max_len: int = self._config.max_chunk_chars
        parts: List[str] = []
        start_index: int = 0
        while start_index < len(sentence):
            end_index: int = min(start_index + max_len, len(sentence))
            parts.append(sentence[start_index:end_index])
            start_index = end_index
        return parts

    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        """对切块结果应用重叠策略。

        参数:
            chunks: 原始切块列表。

        返回值:
            应用重叠后的切块列表。

        关键实现细节:
            每个块追加上一个块末尾的若干字符以增强上下文衔接。
        """

        overlapped: List[str] = []
        for index, chunk in enumerate(chunks):
            if index == 0:
                overlapped.append(chunk)
                continue
            prefix: str = chunks[index - 1][-self._config.overlap_chars:]
            overlapped.append(prefix + chunk)
        return overlapped
