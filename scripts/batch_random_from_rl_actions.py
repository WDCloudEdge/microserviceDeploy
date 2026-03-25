#!/usr/bin/env python3
"""
从 data_nbb/<system>/RL/<N>user 文件里取出 RL 训练得到的 actionlist（maxActions），
把它写进 algorithms/Random/main.py 里的 RMS 变量（cal_kua() 会用 RMS 计算 cross_cost/all_cost/cross_num），
然后对齐 main.py 使用同样的 <N>user_metrics 数据集跑 Random，最后把随机算法分数写回 data_nbb/<system>/RL/<N>user 文件。

要求：
- 外层 main.py 的 metrics 路径会在运行时按 prefix 切成 <N>user_metrics
- Random/main.py 会在运行时被 patch，然后运行结束还原

用法：
  .venv/bin/python scripts/batch_random_from_rl_actions.py --prefixes 10
  .venv/bin/python scripts/batch_random_from_rl_actions.py --prefixes 10 50 90 200 400
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


# def patch_metrics_paths(main_py: str, prefix: int) -> str:
#     pat_graph = re.compile(r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceGraph\.csv['\"])")
#     pat_resource = re.compile(r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceResource\.csv['\"])")
#     s, n1 = pat_graph.subn(rf"\g<1>{prefix}user_metrics/\3", main_py, count=0)
#     s, n2 = pat_resource.subn(rf"\g<1>{prefix}user_metrics/\3", s, count=0)
#     if n1 != 1 or n2 != 1:
#         raise RuntimeError(
#             f"patch_metrics_paths failed for prefix={prefix}: ServiceGraph matches={n1}, ServiceResource matches={n2}"
#         )
#     return s

def patch_metrics_paths(main_py: str, prefix: int) -> str:
    """将 main.py 中两处 .../<N>user_metrics/... 的 N 替换为 prefix。"""
    pat_graph = re.compile(r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceGraph\.csv['\"])")
    pat_resource = re.compile(
        r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceResource\.csv['\"])"
    )
    pat_service_graph = re.compile(
        r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(graph\.csv['\"])"
    )
    s, n1 = pat_graph.subn(rf"\g<1>{prefix}user_metrics/\3", main_py, count=0)
    s, n2 = pat_resource.subn(rf"\g<1>{prefix}user_metrics/\3", s, count=0)
    s, n3 = pat_service_graph.subn(rf"\g<1>{prefix}user_metrics/\3", s, count=0)
    if n1 != 1 or n2 != 1 or n3 != 1:
        raise RuntimeError(
            f"patch_main_metrics_paths failed for prefix={prefix}: "
            f"ServiceGraph matches={n1}, ServiceResource matches={n2}. "
            f"graph matches={n3}. "
            f"请检查 main.py 中是否仍有且仅有一处 ServiceGraph/ServiceResource/graph 路径。"
        )
    return s


def last_non_empty_line(text: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    raise RuntimeError("text is empty")


def extract_actionlist_from_rl_file(text: str) -> list:
    """
    从 RL 文件中提取 maxActions: [...] 里的列表。
    RL/main.py 输出形如：maxReward:... maxActions:[[6, 5], ...]
    """
    # 取最后一行含 maxActions 的
    lines = [l.strip() for l in text.splitlines() if "maxActions:" in l]
    if not lines:
        raise RuntimeError("RL 文件中找不到 maxActions 行")
    line = lines[-1]
    after = line.split("maxActions:", 1)[1].strip()
    start = after.find("[")
    end = after.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise RuntimeError(f"无法解析 maxActions 列表：{line}")
    payload = after[start : end + 1]
    return ast.literal_eval(payload)


def extract_cross_lines(stdout: str) -> dict:
    # 取最后一次出现的 cross_cost/all_cost/cross_num，避免中间日志干扰
    cross_cost = None
    all_cost = None
    cross_num = None
    for line in reversed(stdout.splitlines()):
        if line.strip().startswith("cross_cost:") and cross_cost is None:
            cross_cost = line.strip()
        elif line.strip().startswith("all_cost:") and all_cost is None:
            all_cost = line.strip()
        elif line.strip().startswith("cross_num:") and cross_num is None:
            cross_num = line.strip()
    if not (cross_cost and all_cost and cross_num):
        raise RuntimeError(
            "未从 Random 输出中提取到 cross_cost/all_cost/cross_num。"
            f"stdout 前2000行：\n{stdout[:2000]}"
        )
    return {"cross_cost": cross_cost, "all_cost": all_cost, "cross_num": cross_num}


def patch_random_rms_variable(random_main_text: str, actions: list) -> str:
    rms_line_pattern = re.compile(r"^(?P<indent>\s*)RMS\s*=\s*\[\[.*?\]\]\s*$", re.MULTILINE)
    replacement = r"\g<indent>RMS = " + repr(actions)
    new_text, n = rms_line_pattern.subn(replacement, random_main_text, count=1)
    if n != 1:
        raise RuntimeError("未能唯一匹配 Random/main.py 中 RMS = ... 行，请检查 RMS 赋值格式")
    return new_text


def trim_existing_random_section(lines: list[str]) -> list[str]:
    """
    若文件中曾写入 random_from_rl 片段，则截断（避免重复追加）。
    """
    for i, l in enumerate(lines):
        if l.strip() == "random_from_rl":
            return lines[:i]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefixes", type=int, nargs="+", default=[10, 50, 90, 200, 400])
    parser.add_argument("--python", default=None, help="python 解释器路径（默认 .venv/bin/python）")
    parser.add_argument("--no-restore", action="store_true", help="不还原 Random/main.py")
    args = parser.parse_args()

    root = repo_root()
    config_path = root / "config.json"
    random_main_path = root / "algorithms" / "Random" / "main.py"
    outer_main_path = root / "main.py"

    if not config_path.is_file():
        print(f"找不到 config.json: {config_path}", file=sys.stderr)
        return 1
    if not random_main_path.is_file():
        print(f"找不到 Random/main.py: {random_main_path}", file=sys.stderr)
        return 1
    if not outer_main_path.is_file():
        print(f"找不到 main.py: {outer_main_path}", file=sys.stderr)
        return 1

    cfg = json.loads(read_text(config_path))
    system = cfg.get("system", "hipster")

    if args.python:
        py_exe = args.python
    else:
        venv_py = root / ".venv" / "bin" / "python"
        py_exe = str(venv_py) if venv_py.is_file() else sys.executable

    # 备份并 patch Random/main.py
    random_main_orig = read_text(random_main_path)
    random_backup = root / "algorithms" / "Random" / "main.py.batch_backup"
    if not args.no_restore:
        shutil.copy2(random_main_path, random_backup)

    baseline_main = read_text(outer_main_path)
    env = os.environ.copy()
    env["DRDQL_SKIP_UVICORN"] = "1"

    try:
        for prefix in args.prefixes:
            rl_file = root / "data_nbb" / system / "RL" / f"{prefix}user"
            if not rl_file.is_file():
                raise FileNotFoundError(f"找不到 RL action 文件：{rl_file}")

            rl_text = read_text(rl_file)
            actionlist = extract_actionlist_from_rl_file(rl_text)

            # patch 外层 main.py 数据集路径
            patched_outer_main = patch_metrics_paths(baseline_main, prefix)
            write_text(outer_main_path, patched_outer_main)

            # patch Random/main.py RMS 变量
            patched_random = patch_random_rms_variable(random_main_orig, actionlist)
            write_text(random_main_path, patched_random)

            proc = subprocess.run([py_exe, str(outer_main_path)], cwd=str(root), env=env, capture_output=True, text=True)
            if proc.returncode != 0:
                out = (proc.stdout or "") + (proc.stderr or "")
                raise RuntimeError(f"运行 main.py 失败：prefix={prefix}, rc={proc.returncode}\n输出尾部：\n{out[-4000:]}")

            cross = extract_cross_lines(proc.stdout + "\n" + proc.stderr)

            # 写回到 RL 文件末尾（清除旧 random_from_rl 片段）
            lines = rl_text.splitlines()
            lines = trim_existing_random_section(lines)
            # 保证和原格式一样追加空行分隔
            lines_out = lines + ["", "random_from_rl"]
            lines_out.append(f"actions_used: {repr(actionlist)}")
            lines_out.append(cross["cross_cost"])
            lines_out.append(cross["all_cost"])
            lines_out.append(cross["cross_num"])
            write_text(rl_file, "\n".join(lines_out).rstrip("\n") + "\n")

            print(f"[完成] prefix={prefix} 写回 {rl_file}")
    finally:
        if not args.no_restore:
            # restore Random/main.py & outer main.py
            if random_backup.is_file():
                shutil.copy2(random_backup, random_main_path)
            write_text(outer_main_path, baseline_main)

    return 0


if __name__ == "__main__":
    sys.exit(main())

