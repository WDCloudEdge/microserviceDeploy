#!/usr/bin/env python3
"""
批量切换 main.py 中 metrics 子目录（ServiceGraph / ServiceResource），依次运行 main.py，
并把 algorithms/RSDQL/log.txt 最后两行写入 data_nbb/<system>/RSDQL/<N>user。

规则：
- 若目标文件不存在则创建
- 若目标文件已存在且有内容：先清空再写入（覆盖）
- 批处理运行时设置 DRDQL_SKIP_UVICORN=1，避免 uvicorn 阻塞

用法（在项目根目录 DRDQL 下）:
  .venv/bin/python scripts/batch_rsdql_metrics.py
  .venv/bin/python scripts/batch_rsdql_metrics.py --prefixes 10 50 90 200 400
  .venv/bin/python scripts/batch_rsdql_metrics.py --no-restore
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
    path.write_text(content, encoding="utf-8", newline="\n")


def patch_metrics_paths(main_py: str, prefix: int) -> str:
    """
    精确替换两处硬编码路径：
      dataBaseFilePath + '<N>user_metrics/ServiceGraph.csv'
      dataBaseFilePath + '<N>user_metrics/ServiceResource.csv'
    """
    pat_graph = re.compile(r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceGraph\.csv['\"])")
    pat_resource = re.compile(r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceResource\.csv['\"])")

    s, n1 = pat_graph.subn(rf"\g<1>{prefix}user_metrics/\3", main_py, count=0)
    s, n2 = pat_resource.subn(rf"\g<1>{prefix}user_metrics/\3", s, count=0)

    if n1 != 1 or n2 != 1:
        raise RuntimeError(
            f"patch_metrics_paths failed for prefix={prefix}: "
            f"ServiceGraph matches={n1}, ServiceResource matches={n2}. "
            f"请检查 main.py 中两处路径是否仍为 dataBaseFilePath + '<N>user_metrics/...'"
        )
    return s


def tail_lines(path: Path, n: int) -> list[str]:
    if not path.is_file():
        return []
    lines = read_text(path).splitlines()
    return lines[-n:] if len(lines) >= n else lines


def main() -> int:
    parser = argparse.ArgumentParser(description="批量切换 metrics 并运行 main.py，收集 RSDQL 日志末两行")
    parser.add_argument("--prefixes", type=int, nargs="+", default=[10, 50, 90, 200, 400])
    parser.add_argument("--python", default=None, help="Python 解释器路径，默认使用 .venv/bin/python")
    parser.add_argument("--no-restore", action="store_true", help="结束后不还原 main.py")
    args = parser.parse_args()

    root = repo_root()
    main_path = root / "main.py"
    config_path = root / "config.json"
    rsdql_log = root / "algorithms" / "RSDQL" / "log.txt"
    backup_path = root / "main.py.batch_backup"

    if not main_path.is_file():
        print(f"找不到 main.py: {main_path}", file=sys.stderr)
        return 1
    if not config_path.is_file():
        print(f"找不到 config.json: {config_path}", file=sys.stderr)
        return 1

    baseline_main = read_text(main_path)
    if not args.no_restore:
        shutil.copy2(main_path, backup_path)
        print(f"已备份 main.py -> {backup_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    system = cfg.get("system", "bookinfo")

    py_exe = args.python
    if not py_exe:
        venv_py = root / ".venv" / "bin" / "python"
        py_exe = str(venv_py) if venv_py.is_file() else sys.executable

    env = os.environ.copy()
    env["DRDQL_SKIP_UVICORN"] = "1"

    for prefix in args.prefixes:
        new_content = patch_metrics_paths(baseline_main, prefix)
        write_text(main_path, new_content)
        print(f"\n=== 使用 {prefix}user_metrics 运行 main.py（RSDQL） ===")

        proc = subprocess.run([py_exe, str(main_path)], cwd=str(root), env=env)
        if proc.returncode != 0:
            print(f"main.py 退出码 {proc.returncode}，prefix={prefix}", file=sys.stderr)
            if not args.no_restore and backup_path.is_file():
                shutil.copy2(backup_path, main_path)
                print("已还原 main.py")
            return int(proc.returncode)

        last_two = tail_lines(rsdql_log, 2)
        target = root / "data_nbb" / system / "RSDQL" / f"{prefix}user"
        target.parent.mkdir(parents=True, exist_ok=True)

        # 清空后重新写入
        if target.exists() and target.is_file():
            target.unlink()
        target.write_text("\n".join(last_two) + ("\n" if last_two else ""), encoding="utf-8")
        print(f"已写入最后两行 -> {target}")
        for line in last_two:
            print(f"  | {line}")

    if not args.no_restore and backup_path.is_file():
        shutil.copy2(backup_path, main_path)
        print(f"\n已还原 main.py（来自 {backup_path}）")

    return 0


if __name__ == "__main__":
    sys.exit(main())

