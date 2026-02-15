"""LLM API客户端模块。

该模块提供可配置的API客户端骨架，支持从.env加载密钥并执行基础重试。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
import time
from typing import Dict, List

from dotenv import load_dotenv
import requests


@dataclass(frozen=True)
class LlmClientConfig:
    """LLM客户端配置。

    参数:
        enable: 是否启用API调用。
        base_url: API基础地址。
        api_key_env: API密钥的环境变量名。
        model: 模型标识。
        timeout_seconds: 请求超时时间。
        max_retries: 最大重试次数。

    返回值:
        不直接返回，作为配置对象供客户端使用。

    关键实现细节:
        通过环境变量加载密钥，避免硬编码。
    """

    enable: bool
    base_url: str
    api_key_env: str
    model: str
    timeout_seconds: int
    max_retries: int


class LlmClient:
    """LLM API客户端。

    参数:
        config: LlmClientConfig 配置对象。

    返回值:
        提供文本生成能力。

    关键实现细节:
        统一处理鉴权、超时与重试，并要求返回结构包含text字段。
    """

    def __init__(self, config: LlmClientConfig) -> None:
        """初始化客户端。

        参数:
            config: LlmClientConfig 配置对象。

        返回值:
            无。

        关键实现细节:
            初始化阶段读取.env环境变量。
        """

        self._config: LlmClientConfig = config
        load_dotenv()

    def generate(self, prompt: str) -> str:
        """调用API生成文本。

        参数:
            prompt: 输入提示词。

        返回值:
            生成文本。

        关键实现细节:
            使用简单的JSON协议，要求响应包含text字段。
        """

        if self._config.enable is False:
            raise RuntimeError("LLM客户端未启用")

        api_key: str | None = os.getenv(self._config.api_key_env)
        if api_key is None or api_key.strip() == "":
            raise RuntimeError("API密钥缺失: " + self._config.api_key_env)

        headers: Dict[str, str] = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, object] = {
            "model": self._config.model,
            "prompt": prompt,
        }

        last_error: str = ""
        for attempt in range(self._config.max_retries + 1):
            try:
                response: requests.Response = requests.post(
                    self._config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=self._config.timeout_seconds,
                )
                if response.status_code >= 400:
                    last_error = response.text
                    time.sleep(min(2 ** attempt, 8))
                    continue
                data: Dict[str, object] = response.json()
                text_value: str | None = data.get("text") if isinstance(data, dict) else None
                if text_value is None:
                    raise RuntimeError("响应缺少text字段")
                return str(text_value)
            except requests.RequestException as exc:
                last_error = str(exc)
                time.sleep(min(2 ** attempt, 8))
        raise RuntimeError("API调用失败: " + last_error)

    def score_perplexity(
        self,
        endpoint: str,
        text_field: str,
        logprobs_field: str,
        text: str,
    ) -> float:
        """调用API计算困惑度。

        参数:
            endpoint: 困惑度API地址。
            text_field: 请求体中文本字段名。
            logprobs_field: 响应中对数概率列表字段名。
            text: 输入文本。

        返回值:
            困惑度数值。

        关键实现细节:
            根据token对数概率计算 $\exp(-\bar{\ell})$。
        """

        if self._config.enable is False:
            raise RuntimeError("LLM客户端未启用")

        api_key: str | None = os.getenv(self._config.api_key_env)
        if api_key is None or api_key.strip() == "":
            raise RuntimeError("API密钥缺失: " + self._config.api_key_env)

        headers: Dict[str, str] = {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        }
        payload: Dict[str, object] = {
            "model": self._config.model,
            text_field: text,
        }

        last_error: str = ""
        for attempt in range(self._config.max_retries + 1):
            try:
                response: requests.Response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self._config.timeout_seconds,
                )
                if response.status_code >= 400:
                    last_error = response.text
                    time.sleep(min(2 ** attempt, 8))
                    continue
                data: Dict[str, object] = response.json()
                logprobs: List[float] | None = data.get(logprobs_field) if isinstance(data, dict) else None
                if logprobs is None or len(logprobs) == 0:
                    raise RuntimeError("响应缺少logprobs列表")
                average_logprob: float = sum(logprobs) / float(len(logprobs))
                return math.exp(-average_logprob)
            except requests.RequestException as exc:
                last_error = str(exc)
                time.sleep(min(2 ** attempt, 8))
        raise RuntimeError("困惑度API调用失败: " + last_error)
