"""类型定义。

该模块集中定义跨模块共享的类型别名，提升可读性与一致性。
"""

from typing import Dict, List, Union

PlanItem = Dict[str, Union[int, str]]
Plan = List[PlanItem]
Metrics = Dict[str, Union[int, float, str]]
Stats = Dict[str, Union[int, float, str]]
Diagnostics = Dict[str, Union[str, None, Metrics, Stats, Plan]]
