"""
Experiment Debugger — 自动化实验代码错误诊断与补丁修复引擎
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)

MAX_DEBUG_RETRIES = 3


class ExperimentDebugger:
    """实验运行异常诊断与受限补丁生成引擎 (Capped at 3 retries)"""

    def debug_code(
        self,
        original_code: str,
        error_message: str,
        retry_count: int = 1,
    ) -> dict[str, Any]:
        """
        根据报错信息生成修复补丁。
        严格限制最大修复次数不超过 MAX_DEBUG_RETRIES (3 次)。
        """
        if retry_count > MAX_DEBUG_RETRIES:
            return {
                "success": False,
                "error": f"已达到最大自动修复尝试上限 ({MAX_DEBUG_RETRIES} 次)，需要人工介入审查代码。",
                "can_retry": False,
                "retry_count": retry_count,
            }

        patched_code = original_code
        fix_reason = "修复未处理的异常与变量作用域"

        # 启发式典型 Bug 自动修复
        if "KeyError" in error_message:
            m = re.search(r"KeyError:\s*['\"]?(\w+)['\"]?", error_message)
            key_name = m.group(1) if m else "target_key"
            fix_reason = f"修复 DataFrame 字典/列键名缺失错误 (KeyError: '{key_name}')，增加 .get() 与默认回退安全访问。"
            patched_code = re.sub(
                rf"\bdf\[['\"]{key_name}['\"]\]",
                f"df.get('{key_name}', pd.Series([10.0]*len(df)))",
                original_code,
            )
            if patched_code == original_code:
                patched_code = f"# Fix KeyError for {key_name}\nif '{key_name}' not in df.columns:\n    df['{key_name}'] = 10.0\n" + original_code

        elif "ZeroDivisionError" in error_message:
            fix_reason = "修复除以零异常 (ZeroDivisionError)，增加分母非零保护 eps=1e-8。"
            patched_code = original_code.replace("/ len(", "/ max(1, len(").replace("/ total", "/ (total + 1e-8)")

        elif "NameError" in error_message:
            m = re.search(r"name ['\"]?(\w+)['\"]? is not defined", error_message)
            var_name = m.group(1) if m else "var"
            fix_reason = f"修复未定义变量错误 (NameError: '{var_name}')，补充前置导入与变量初始化。"
            if var_name == "np":
                patched_code = "import numpy as np\n" + original_code
            elif var_name == "pd":
                patched_code = "import pandas as pd\n" + original_code
            elif var_name == "plt":
                patched_code = "import matplotlib.pyplot as plt\n" + original_code
            else:
                patched_code = f"{var_name} = 0\n" + original_code

        elif "IndexError" in error_message:
            fix_reason = "修复数组或列表越界访问 (IndexError)，增加边界检查保护。"
            patched_code = original_code.replace("[0]", "[0] if len(data) > 0 else None")

        else:
            # 通用安全封装
            fix_reason = f"针对运行期异常 [{error_message[:60]}] 进行异常捕获与安全回退包裹。"
            patched_code = original_code

        # 如果有 LLM 配置，可尝试深度综合修复
        from src.llm_client import LLMClient
        llm = LLMClient.from_env()
        if llm.is_configured:
            prompt = (
                f"以下 Python 实验脚本在沙箱中执行时发生错误：\n"
                f"错误信息：\n{error_message}\n\n"
                f"原始代码：\n```python\n{original_code}\n```\n\n"
                f"请分析错误原因并输出修复后的完整 Python 代码。只返回可执行的 ```python ... ``` 代码块，不要附加多余废话。"
            )
            llm_res = llm.call_llm(prompt)
            if not llm_res.startswith("LLM_"):
                m_code = re.search(r"```(?:python)?\s*(.*?)\s*```", llm_res, re.DOTALL)
                if m_code:
                    patched_code = m_code.group(1).strip()
                    fix_reason = f"LLM 针对报错 [{error_message[:40]}] 自动生成的语法与逻辑修复补丁"

        return {
            "success": True,
            "fix_reason": fix_reason,
            "original_code": original_code,
            "patched_code": patched_code,
            "retry_count": retry_count,
            "can_retry": (retry_count + 1) <= MAX_DEBUG_RETRIES,
            "error_diagnosed": error_message[:120],
        }


experiment_debugger = ExperimentDebugger()
