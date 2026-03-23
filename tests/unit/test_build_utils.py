"""
tests.unit.test_build_utils 的 Docstring
确保 resolve_target_dirs 函数在不同输入情况下正确返回目标目录列表
""" 
from src.build_utils import resolve_target_dirs


def test_resolve_target_dirs_without_learn_dir():
    assert resolve_target_dirs("./data/raw/docs") == ["./data/raw/docs"]


def test_resolve_target_dirs_with_learn_dir():
    assert resolve_target_dirs("./data/raw/docs", "./data/raw_learn") == [
        "./data/raw/docs",
        "./data/raw_learn",
    ]


def test_resolve_target_dirs_with_blank_learn_dir():
    assert resolve_target_dirs("./data/raw/docs", "   ") == ["./data/raw/docs"]
