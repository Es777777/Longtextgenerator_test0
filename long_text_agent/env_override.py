"""环境变量覆盖配置。

该模块提供将环境变量覆盖到显式配置上的辅助函数。
"""

from __future__ import annotations

import os
from typing import List

from .ast_grep_splitter import AstGrepConfig
from .config import AgentConfig
from .llm_client import LlmClientConfig
from .perplexity import PerplexityConfig
from .text_type import TextTypeConfig


def apply_env_overrides(config: AgentConfig) -> AgentConfig:
    """使用环境变量覆盖配置。

    参数:
        config: 原始AgentConfig配置对象。

    返回值:
        覆盖后的AgentConfig配置对象。

    关键实现细节:
        仅在环境变量存在时覆盖，避免引入隐式默认值。
    """

    ast_grep: AstGrepConfig = _override_ast_grep(config.ast_grep)
    text_type: TextTypeConfig = _override_text_type(config.text_type)
    llm_client: LlmClientConfig = _override_llm_client(config.llm_client)
    perplexity: PerplexityConfig = _override_perplexity(config.perplexity)

    return AgentConfig(
        max_chunk_chars=_override_int("MAX_CHUNK_CHARS", config.max_chunk_chars),
        overlap_chars=_override_int("OVERLAP_CHARS", config.overlap_chars),
        enable_overlap=_override_bool("ENABLE_OVERLAP", config.enable_overlap),
        summary_chars=_override_int("SUMMARY_CHARS", config.summary_chars),
        enable_self_check=_override_bool("ENABLE_SELF_CHECK", config.enable_self_check),
        ast_grep=ast_grep,
        text_type=text_type,
        llm_client=llm_client,
        perplexity=perplexity,
    )


def _override_ast_grep(config: AstGrepConfig) -> AstGrepConfig:
    """覆盖AST-GREP配置。

    参数:
        config: 原始AstGrepConfig配置对象。

    返回值:
        覆盖后的AstGrepConfig配置对象。

    关键实现细节:
        patterns支持以逗号分隔的环境变量形式。
    """

    patterns_value: List[str] = config.patterns
    env_patterns: str | None = os.getenv("AST_GREP_PATTERNS")
    if env_patterns is not None:
        patterns_value = [item.strip() for item in env_patterns.split(",") if item.strip() != ""]

    return AstGrepConfig(
        enable=_override_bool("AST_GREP_ENABLE", config.enable),
        command=_override_str("AST_GREP_COMMAND", config.command),
        language=_override_str("AST_GREP_LANGUAGE", config.language),
        patterns=patterns_value,
    )


def _override_text_type(config: TextTypeConfig) -> TextTypeConfig:
    """覆盖文本类型检测配置。

    参数:
        config: 原始TextTypeConfig配置对象。

    返回值:
        覆盖后的TextTypeConfig配置对象。

    关键实现细节:
        正则配置仅在环境变量存在时覆盖。
    """

    return TextTypeConfig(
        min_score=_override_int("TEXT_TYPE_MIN_SCORE", config.min_score),
        line_ratio_divisor=_override_int("TEXT_TYPE_LINE_RATIO_DIVISOR", config.line_ratio_divisor),
        keyword_weight=_override_int("TEXT_TYPE_KEYWORD_WEIGHT", config.keyword_weight),
        symbol_weight=_override_int("TEXT_TYPE_SYMBOL_WEIGHT", config.symbol_weight),
        line_weight=_override_int("TEXT_TYPE_LINE_WEIGHT", config.line_weight),
        keyword_pattern=_override_str("TEXT_TYPE_KEYWORD_PATTERN", config.keyword_pattern),
        symbol_pattern=_override_str("TEXT_TYPE_SYMBOL_PATTERN", config.symbol_pattern),
        line_start_pattern=_override_str("TEXT_TYPE_LINE_START_PATTERN", config.line_start_pattern),
        call_like_pattern=_override_str("TEXT_TYPE_CALL_LIKE_PATTERN", config.call_like_pattern),
        comment_pattern=_override_str("TEXT_TYPE_COMMENT_PATTERN", config.comment_pattern),
    )


def _override_llm_client(config: LlmClientConfig) -> LlmClientConfig:
    """覆盖LLM客户端配置。

    参数:
        config: 原始LlmClientConfig配置对象。

    返回值:
        覆盖后的LlmClientConfig配置对象。

    关键实现细节:
        enable开关允许通过环境变量快速切换。
    """

    return LlmClientConfig(
        enable=_override_bool("LLM_ENABLE", config.enable),
        base_url=_override_str("LLM_BASE_URL", config.base_url),
        api_key_env=_override_str("LLM_API_KEY_ENV", config.api_key_env),
        model=_override_str("LLM_MODEL", config.model),
        timeout_seconds=_override_int("LLM_TIMEOUT_SECONDS", config.timeout_seconds),
        max_retries=_override_int("LLM_MAX_RETRIES", config.max_retries),
    )


def _override_perplexity(config: PerplexityConfig) -> PerplexityConfig:
    """覆盖困惑度配置。

    参数:
        config: 原始PerplexityConfig配置对象。

    返回值:
        覆盖后的PerplexityConfig配置对象。

    关键实现细节:
        支持通过环境变量启用与替换字段名。
    """

    return PerplexityConfig(
        enable=_override_bool("PERPLEXITY_ENABLE", config.enable),
        endpoint=_override_str("PERPLEXITY_ENDPOINT", config.endpoint),
        text_field=_override_str("PERPLEXITY_TEXT_FIELD", config.text_field),
        logprobs_field=_override_str("PERPLEXITY_LOGPROBS_FIELD", config.logprobs_field),
    )


def _override_int(env_key: str, default_value: int) -> int:
    """从环境变量读取整数覆盖值。

    参数:
        env_key: 环境变量名。
        default_value: 默认值。

    返回值:
        覆盖后的整数值。

    关键实现细节:
        仅在环境变量存在时覆盖。
    """

    raw: str | None = os.getenv(env_key)
    if raw is None:
        return default_value
    return int(raw)


def _override_bool(env_key: str, default_value: bool) -> bool:
    """从环境变量读取布尔覆盖值。

    参数:
        env_key: 环境变量名。
        default_value: 默认值。

    返回值:
        覆盖后的布尔值。

    关键实现细节:
        支持true/false/1/0/yes/no等常见形式。
    """

    raw: str | None = os.getenv(env_key)
    if raw is None:
        return default_value
    normalized: str = raw.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default_value


def _override_str(env_key: str, default_value: str) -> str:
    """从环境变量读取字符串覆盖值。

    参数:
        env_key: 环境变量名。
        default_value: 默认值。

    返回值:
        覆盖后的字符串。

    关键实现细节:
        仅在环境变量存在且非空时覆盖。
    """

    raw: str | None = os.getenv(env_key)
    if raw is None:
        return default_value
    if raw.strip() == "":
        return default_value
    return raw
