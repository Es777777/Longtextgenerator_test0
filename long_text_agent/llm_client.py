"""LLM API客户端模块。

该模块提供可配置的API客户端骨架，支持从.env加载密钥并执行基础重试。
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import os
from pathlib import Path
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
    generate_path: str
    auth_type: str


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
        self._session = requests.Session()

    def _read_api_key(self) -> str:
        """读取API密钥。

        参数:
            无。

        返回值:
            API密钥字符串。

        关键实现细节:
            优先读环境变量，缺失时回退至用户主目录 `~/.longtext_secrets`。
        """

        api_key: str | None = os.getenv(self._config.api_key_env)
        if api_key is not None and api_key.strip() != "":
            return api_key.strip()

        secrets_path: Path = Path.home() / ".longtext_secrets"
        if secrets_path.exists():
            with secrets_path.open() as file_obj:
                for raw_line in file_obj:
                    line: str = raw_line.strip()
                    if line == "" or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key_name, key_value = line.split("=", 1)
                    if key_name.strip() == self._config.api_key_env and key_value.strip() != "":
                        return key_value.strip()

        raise RuntimeError("API密钥缺失: " + self._config.api_key_env)

    def _build_auth_headers(self, api_key: str) -> Dict[str, str]:
        """构建鉴权请求头。

        参数:
            api_key: API密钥。

        返回值:
            请求头字典。

        关键实现细节:
            `auth_type` 为 `bearer` 时使用 Authorization，否则把 `auth_type` 当作头名。
        """

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        auth_type: str = (self._config.auth_type or "bearer").strip()
        if auth_type.lower() in {"bearer", "authorization", "auth"}:
            headers["Authorization"] = "Bearer " + api_key
        else:
            headers[auth_type] = api_key
        return headers

    def _build_generate_url(self) -> str:
        """生成文本接口URL。

        参数:
            无。

        返回值:
            最终请求URL。

        关键实现细节:
            第一阶段：若配置了 `generate_path`，直接拼接。
            第二阶段：未配置时，按保守规则推断路径，避免重复追加 `/v1`。
        """

        base: str = self._config.base_url.rstrip("/")
        generate_path: str = (self._config.generate_path or "").strip()

        # 第一阶段：显式路径优先
        if generate_path != "":
            if generate_path.startswith("/"):
                return base + generate_path
            return base + "/" + generate_path

        # 第二阶段：保守回退
        if base.endswith("/v1"):
            return base + "/generate"
        if base.endswith("/anthropic"):
            return base + "/v1/messages"
        return base

    def _build_generate_payload(self, request_url: str, prompt: str) -> Dict[str, object]:
        """构建生成请求体。

        参数:
            request_url: 最终请求URL。
            prompt: 输入提示词。

        返回值:
            请求体字典。

        关键实现细节:
            对 OpenAI 兼容路径（如 `/chat/completions`）使用 `messages`，
            其余路径保留 `prompt` 协议。
        """

        lowered_url: str = request_url.lower()
        if "/anthropic/v1/messages" in lowered_url or lowered_url.endswith("/v1/messages"):
            return {
                "model": self._config.model,
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            }
        if "/chat/completions" in lowered_url:
            return {
                "model": self._config.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            }
        return {
            "model": self._config.model,
            "prompt": prompt,
        }

    def _extract_generated_text(self, data: Dict[str, object]) -> str:
        """从响应中提取文本。

        参数:
            data: JSON响应字典。

        返回值:
            提取到的文本。

        关键实现细节:
            兼容两类响应：
            1) 传统 `text` 字段；
            2) OpenAI 风格 `choices[0].message.content` 或 `choices[0].text`。
        """

        text_value: object = data.get("text")
        if isinstance(text_value, str) and text_value.strip() != "":
            return text_value

        choices_value: object = data.get("choices")
        if isinstance(choices_value, list) and len(choices_value) > 0:
            first_choice: object = choices_value[0]
            if isinstance(first_choice, dict):
                message_obj: object = first_choice.get("message")
                if isinstance(message_obj, dict):
                    content_obj: object = message_obj.get("content")
                    if isinstance(content_obj, str) and content_obj.strip() != "":
                        return content_obj
                direct_text: object = first_choice.get("text")
                if isinstance(direct_text, str) and direct_text.strip() != "":
                    return direct_text

        content_value: object = data.get("content")
        if isinstance(content_value, list) and len(content_value) > 0:
            for block in content_value:
                if isinstance(block, dict):
                    block_text: object = block.get("text")
                    if isinstance(block_text, str) and block_text.strip() != "":
                        return block_text

        raise RuntimeError("响应缺少可解析文本字段")

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

        api_key: str = self._read_api_key()
        headers: Dict[str, str] = self._build_auth_headers(api_key)
        request_url: str = self._build_generate_url()
        payload: Dict[str, object] = self._build_generate_payload(request_url, prompt)

        last_error: str = ""
        for attempt in range(self._config.max_retries + 1):
            try:
                response: requests.Response = self._session.post(
                    request_url,
                    headers=headers,
                    json=payload,
                    timeout=self._config.timeout_seconds,
                    allow_redirects=True,
                )
                if response.status_code >= 400:
                    last_error = f"status={response.status_code} url={response.url} body={response.text}"
                    time.sleep(min(2 ** attempt, 8))
                    continue
                data: Dict[str, object] = response.json()
                return self._extract_generated_text(data)
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

        api_key: str = self._read_api_key()
        headers: Dict[str, str] = self._build_auth_headers(api_key)
        payload: Dict[str, object] = {
            "model": self._config.model,
            text_field: text,
        }

        last_error: str = ""
        for attempt in range(self._config.max_retries + 1):
            try:
                response: requests.Response = self._session.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=self._config.timeout_seconds,
                    allow_redirects=True,
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
