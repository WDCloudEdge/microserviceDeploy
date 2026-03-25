#!/usr/bin/env python3
"""
按论文定义的标量 β 批量运行 RL，并写出结果。

对每个 β ∈ {0,0.2,0.4,0.6,0.8,1.0} 和每个 prefix ∈ {10,50,90,200,400}：
1) patch 最外层 main.py 两处 <N>user_metrics 路径
2) 运行 main.py（需要 config.json.algorithm=RL）
   - 环境变量 DRDQL_BETA=<β>
   - DRDQL_SKIP_UVICORN=1
3) 从根目录 log.txt 中取最后一条包含 maxActions: 的行
4) 写入 data_nbb/<system>/RL_beta/beta_<β>/<N>user（覆盖写）
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
    pat_graph = re.compile(r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceGraph\.csv['\"])")
    pat_resource = re.compile(r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceResource\.csv['\"])")
    s, n1 = pat_graph.subn(rf"\g<1>{prefix}user_metrics/\3", main_py, count=0)
    s, n2 = pat_resource.subn(rf"\g<1>{prefix}user_metrics/\3", s, count=0)
    if n1 != 1 or n2 != 1:
        raise RuntimeError(
            f"patch_main_metrics_paths failed for prefix={prefix}: ServiceGraph matches={n1}, ServiceResource matches={n2}"
        )
    return s


def last_matching_line(text: str, needle: str) -> str:
    for line in reversed(text.splitlines()):
        if line.strip() and needle in line:
            return line.strip()
    raise RuntimeError(f"未找到包含 {needle!r} 的日志行")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefixes", type=int, nargs="+", default=[10, 50, 90, 200, 400])
    parser.add_argument("--betas", type=float, nargs="+", default=[0, 0.2, 0.4, 0.6, 0.8, 1.0])
    parser.add_argument("--python", default=None, help="python 解释器路径（默认 .venv/bin/python）")
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
    backup_path = root / "main.py.batch_rl_beta_backup"
    if not args.no_restore:
        shutil.copy2(main_path, backup_path)

    cfg = json.loads(read_text(config_path))
    system = cfg.get("system", "bookinfo")

    if args.python:
        py_exe = args.python
    else:
        venv_py = root / ".venv" / "bin" / "python"
        py_exe = str(venv_py) if venv_py.is_file() else sys.executable

    try:
        for beta in args.betas:
            beta_tag = f"beta_{beta:.1f}".replace(".", "_")
            for prefix in args.prefixes:
                patched = patch_main_metrics_paths(baseline_main, prefix)
                write_text(main_path, patched)

                env = os.environ.copy()
                env["DRDQL_SKIP_UVICORN"] = "1"
                env["DRDQL_BETA"] = str(beta)

                proc = subprocess.run(
                    [py_exe, str(main_path)],
                    cwd=str(root),
                    env=env,
                    capture_output=True,
                    text=True,
                )
                if proc.returncode != 0:
                    out = (proc.stdout or "") + (proc.stderr or "")
                    raise RuntimeError(f"RL run failed: beta={beta} prefix={prefix} rc={proc.returncode}\n{out[-4000:]}")

                line = last_matching_line(read_text(log_path), "maxActions:")

                out_file = root / "data_nbb" / system / "RL_beta" / beta_tag / f"{prefix}user"
                if out_file.exists() and out_file.is_file():
                    out_file.unlink()
                out_file.parent.mkdir(parents=True, exist_ok=True)
                out_file.write_text(line + "\n", encoding="utf-8")
                print(f"[ok] beta={beta} prefix={prefix} -> {out_file}")
    finally:
        if not args.no_restore and backup_path.is_file():
            shutil.copy2(backup_path, main_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())

