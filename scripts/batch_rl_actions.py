#!/usr/bin/env python3
"""
批量收集 RL 算法 actionlist（以最外层 DRDQL/main.py 的根 log.txt 最后一行为准）。

流程（与之前 RMS/RSDQL->Random 批处理思路一致）：
1) 依次处理 prefix：10 50 90 200 400
2) 修改最外层 main.py 中两处 user_metrics 路径的 N：... '<N>user_metrics/ServiceGraph.csv'
   与 ... '<N>user_metrics/ServiceResource.csv'
3) 清空根目录 log.txt
4) 设置 DRDQL_SKIP_UVICORN=1，执行最外层 main.py
5) 读取根目录 log.txt 的最后一行（最后一个非空行）
6) 写入 data_nbb/<system>/RL/<N>user 文件：存在则清空重写，不存在则创建

用法：
  .venv/bin/python scripts/batch_rl_actions.py --prefixes 10 50 90 200 400
"""

from __future__ import annotations

import argparse
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


def patch_main_metrics_paths(main_py: str, prefix: int) -> str:
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


def last_non_empty_line(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"找不到 log 文件：{path}")
    lines = read_text(path).splitlines()
    for line in reversed(lines):
        if line.strip():
            return line.strip()
    raise RuntimeError(f"log 文件 {path} 为空或没有非空行")


def last_matching_line(path: Path, pattern: str) -> str:
    """
    返回文件中最后一行（按出现顺序）包含 pattern 的非空行。
    """
    if not path.is_file():
        raise FileNotFoundError(f"找不到 log 文件：{path}")
    lines = read_text(path).splitlines()
    for line in reversed(lines):
        if line.strip() and pattern in line:
            return line.strip()
    raise RuntimeError(f"log 文件中找不到包含 pattern={pattern!r} 的行：{path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="批量收集 RL actionlist（取根 log.txt 最后一行）")
    parser.add_argument("--prefixes", type=int, nargs="+", default=[10, 50, 90, 200, 400])
    parser.add_argument("--python", default=None, help="python 解释器路径，默认 .venv/bin/python")
    parser.add_argument("--no-restore", action="store_true", help="不还原 main.py")
    args = parser.parse_args()

    root = repo_root()
    main_path = root / "main.py"
    config_path = root / "config.json"
    log_path = root / "log.txt"

    if not main_path.is_file():
        print(f"找不到 main.py: {main_path}", file=sys.stderr)
        return 1
    if not config_path.is_file():
        print(f"找不到 config.json: {config_path}", file=sys.stderr)
        return 1

    baseline_main = read_text(main_path)
    backup_path = root / "main.py.batch_rl_backup"
    if not args.no_restore:
        shutil.copy2(main_path, backup_path)
        print(f"已备份 main.py -> {backup_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    system = cfg.get("system", "bookinfo")
    user = cfg.get("user", "nbb")  # 仅用于兼容输出目录逻辑（通常不影响 RL 输出文件名）

    if args.python:
        py_exe = args.python
    else:
        venv_py = root / ".venv" / "bin" / "python"
        py_exe = str(venv_py) if venv_py.is_file() else sys.executable

    env = os.environ.copy()
    env["DRDQL_SKIP_UVICORN"] = "1"

    for prefix in args.prefixes:
        # 1) patch main.py 两处 metrics 路径
        patched_main = patch_main_metrics_paths(baseline_main, prefix)
        write_text(main_path, patched_main)
        print(f"\n=== 使用 {prefix}user_metrics 运行 main.py（RL）==={system}")

        # 2) clear root log.txt
        if log_path.is_file():
            log_path.write_text("", encoding="utf-8")

        proc = subprocess.run(
            [py_exe, str(main_path)],
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            out = (proc.stdout or "") + (proc.stderr or "")
            raise RuntimeError(f"运行 main.py 失败：prefix={prefix}, rc={proc.returncode}\n输出尾部：\n{out[-4000:]}")

        # 3) take last line
        # RL 的 actionlist 在 algorithms/RL/main.py 里输出为：maxReward:... maxActions:...
        try:
            last_line = last_matching_line(log_path, "maxActions:")
        except Exception:
            # 兜底：仍取最后一条非空行
            last_line = last_non_empty_line(log_path)

        # 4) write to data_nbb/<system>/RL/<prefix>user
        out_file = root / "data_nbb" / system / "RL" / f"{prefix}user"
        if out_file.exists() and out_file.is_file():
            out_file.unlink()
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(last_line + "\n", encoding="utf-8")
        print(f"已写入：{out_file}")

    if not args.no_restore and backup_path.is_file():
        shutil.copy2(backup_path, main_path)
        print(f"\n已还原 main.py（来自 {backup_path}）")

    return 0


if __name__ == "__main__":
    sys.exit(main())

