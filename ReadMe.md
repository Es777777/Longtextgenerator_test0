# 长文本生成基础Agent

本项目提供一个最小可用的长文本生成策略Agent，用于研究与工程混合场景下的快速验证。当前实现强调可扩展骨架与完整诊断输出，便于后续替换拆分、规划、生成与自检策略。

## 模块结构

入口位于 long_text_agent.py，实际实现位于 long_text_agent 包内。整体以“拆分—规划—生成—自检”组织，各模块职责清晰，便于单独替换或增强。

## 主要流程

拆分阶段先判断文本类型，代码文本优先使用AST-GREP语义切块，匹配失败时回退为标点与定长切块；自然语言文本优先采用层次化拆分（标题优先、无标题按段落），必要时回退为标点切块。规划阶段将切块压缩为摘要与索引，生成阶段基于规划生成长文本，自检阶段输出基础指标与统计信息。

## 功能说明

本Agent面向“长文本生成策略验证”场景，强调可观察性和可扩展性。拆分模块提供显式上下文控制；规划模块提供结构化组织；生成模块既可占位输出也可接入API；自检与统计模块提供最小可用质量信号，便于后续策略迭代对比。

## 配置说明

AgentConfig 不提供默认值，所有字段必须显式填写。AstGrepConfig 用于代码语义拆分，TextTypeConfig 控制文本类型检测的阈值、权重与正则，LlmClientConfig 用于API接入参数与重试控制。

## 使用方式

使用流程为：配置初始化、Agent实例化、调用 run 执行。run 需要 instruction 与 context_text 两个输入，分别代表任务指令与原始上下文文本。return_diagnostics 为 True 时返回诊断信息，适合做研究与评估；为 False 时仅返回最终输出。

示例：

```python
from long_text_agent import AgentConfig, AstGrepConfig, LongTextAgent
from long_text_agent import LlmClientConfig, PerplexityConfig, TextTypeConfig, apply_env_overrides

ast_grep_config = AstGrepConfig(
    enable=True,
    command="sg",
    language="python",
    patterns=[
        "(function_definition)",
        "(class_definition)",
    ],
)

text_type_config = TextTypeConfig(
    min_score=3,
    line_ratio_divisor=3,
    keyword_weight=2,
    symbol_weight=1,
    line_weight=2,
    keyword_pattern=r"\b(def|class|import|from|return|if|else|for|while|try|except|function|const|let|var|public|private|#include)\b",
    symbol_pattern=r"[{}();=<>\[\]]",
    line_start_pattern=r"^\s*(def|class|import|from|#include)\b",
    call_like_pattern=r"^\s*[^\s]+\s*\([^)]*\)\s*\{?\s*$",
    comment_pattern=r"^\s*//|^\s*#",
)

llm_client_config = LlmClientConfig(
    enable=True,
    base_url="https://your-llm-provider/v1/generate",
    api_key_env="LLM_API_KEY",
    model="your-model-name",
    timeout_seconds=60,
    max_retries=2,
)

perplexity_config = PerplexityConfig(
    enable=False,
    endpoint="https://your-llm-provider/v1/logprobs",
    text_field="prompt",
    logprobs_field="logprobs",
)

config = AgentConfig(
    max_chunk_chars=800,
    overlap_chars=80,
    enable_overlap=True,
    summary_chars=120,
    enable_self_check=True,
    ast_grep=ast_grep_config,
    text_type=text_type_config,
    llm_client=llm_client_config,
    perplexity=perplexity_config,
)

config = apply_env_overrides(config)

agent = LongTextAgent(config)
result = agent.run(
    instruction="请根据上下文生成一份结构化长文说明",
    context_text="这里是很长的输入文本……",
    return_diagnostics=True,
)

output_text = result["output"]
metrics = result["metrics"]
stats = result["stats"]
plan = result["plan"]
```

## 诊断输出说明

当 return_diagnostics 为 True 时返回字典包含 output、loss、metrics、stats 与 plan。output 为最终长文本；loss 预留为后续模型集成使用；metrics 为自检指标（如输出长度与去重比例）；stats 为拆分统计信息（如切块数量与平均长度）；plan 为规划条目列表，便于追溯每段输出对应的切块来源。

## API接入说明

当前生成模块已提供API客户端骨架，可通过配置启用外部LLM。LlmClientConfig 控制调用开关、地址、模型、超时与重试；API密钥通过环境变量读取，适合在服务器或容器中部署。默认请求体包含 model 与 prompt 字段，响应需包含 text 字段。若你的API协议不同，可在 LlmClient 内调整请求与解析逻辑。

API密钥示例：

```env
LLM_API_KEY=your_api_key_here
```

## 困惑度自检说明

若需要更严格的质量自检，可启用困惑度计算。该模式要求提供一个返回 token 对数概率列表的API端点，系统将基于 $\exp(-\bar{\ell})$ 计算困惑度，并写入 metrics。具体字段名由 PerplexityConfig 控制。

## 环境变量覆盖说明

项目提供 apply_env_overrides 用于将 .env 中的调试参数覆盖到显式配置上。仅当环境变量存在时才覆盖，避免引入隐式默认值。可用的变量示例见 example.env。

## 依赖说明

若启用AST-GREP语义拆分，需要在运行环境中安装AST-GREP命令行工具，并确保 command 指向可执行入口。未安装或命令不可用时会在运行时抛出异常，便于快速定位环境问题。

## requirements与uv配置

项目提供 requirements.txt 便于依赖安装。若使用 uv，可直接基于 pyproject.toml 进行依赖解析与安装，两种方式任选其一即可。

## 当前限制

生成策略在未启用API时为占位式实现，不依赖外部模型，主要用于骨架验证与流程调试。后续可在各模块内替换为更复杂的策略实现。

## 更新日志

当前阶段已完成基础Agent构造，并引入以下能力：AST-GREP语义拆分、自然语言层次化拆分与困惑度自检机制，同时提供API接入骨架与环境变量覆盖配置。
