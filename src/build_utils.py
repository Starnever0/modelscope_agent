"""
src.build_utils 的 Docstring
包含构建过程中使用的实用函数，例如 resolve_target_dirs，用于确定目标目录列表。
"""
from typing import Optional


def resolve_target_dirs(data_raw_dir: str, learn_dir: Optional[str] = None) -> list[str]:
    target_dirs = [data_raw_dir]
    if isinstance(learn_dir, str) and learn_dir.strip():
        target_dirs.append(learn_dir)
    return target_dirs
