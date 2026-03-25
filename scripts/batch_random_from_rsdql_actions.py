#!/usr/bin/env python3
"""
从 data_nbb/<system>/RSDQL/<N>user 文件中读取两条带 Actions: 的 actionlist（通常是 rsdql_last/rsdql_best），
按 Random 的 cost 计算方式（deployw + ServiceGraph）跑分，并把结果写回同一个文件。

步骤与 RMS_DDPG->Random 跑分保持一致：
- 每个 prefix 先把外层 main.py 的 93/112 行 metrics 前缀切到 Nuser_metrics
- 对读取到的两个 actionlist 分别计算 cross_cost/all_cost/cross_num
- 在文件末尾追加 run1/run2（含 actions_used）
- 若文件中已存在旧的 run1/run2/best/last/run* 块，先清掉再写
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import os
import re
import shutil
import sys
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


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


def read_service_graph_csv(path: Path) -> list[list[float]]:
    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        rows: list[list[float]] = []
        for row in reader:
            rows.append([float(x) for x in row[1:]])
        return rows


def deployw(a, b) -> bool:
    # 与 algorithms/Random/main.py 保持一致的网段划分
    if a[1] < 2 and b[1] < 2:
        return True
    elif 2 <= a[1] < 4 and 2 <= b[1] < 4:
        return True
    elif 4 <= a[1] < 6 and 4 <= b[1] < 6:
        return True
    return False


def calc_costs(service_graph: list[list[float]], action: list[list[int]]) -> tuple[float, float, int]:
    cross_cost = 0.0
    all_cost = 0.0
    cross_num = 0
    for c1 in action:
        s1 = int(c1[0])
        for s2, w in enumerate(service_graph[s1]):
            if w != 0:
                for c2 in action:
                    if int(c2[0]) == s2:
                        if (not deployw(c1, c2)) and service_graph[s1][s2] != 0:
                            cross_cost += service_graph[s1][s2]
                            cross_num += 1
                        all_cost += service_graph[s1][s2]
    return cross_cost, all_cost, cross_num


def parse_actions_from_line(line: str) -> list:
    if "Actions:" not in line:
        raise ValueError(f"该行不包含 Actions: {line}")
    after = line.split("Actions:", 1)[1].strip()
    start = after.find("[")
    end = after.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"无法解析 Actions 列表：line={line}")
    payload = after[start : end + 1]
    return ast.literal_eval(payload)


def extract_latest_two_actions_lines(text: str) -> list[str]:
    """
    取文件中最后出现的两条包含 Actions: 的行（按出现顺序返回）。
    """
    action_lines = [l.strip() for l in text.splitlines() if "Actions:" in l]
    if len(action_lines) < 2:
        raise ValueError("文件中不足两条包含 Actions: 的行")
    return action_lines[-2:]


def trim_existing_runs(lines: list[str]) -> list[str]:
    """
    清掉旧的 run 块：遇到 run1/run2/best/last 这类独立行就截断。
    """
    for i, l in enumerate(lines):
        s = l.strip()
        if s in ("run1", "run2", "best", "last"):
            return lines[:i]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefixes", type=int, nargs="+", default=[10, 50, 90, 200, 400])
    args = parser.parse_args()

    root = repo_root()
    config_path = root / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    system = cfg.get("system", "bookinfo")
    user = cfg.get("user", "nbb")
    run_type = cfg.get("type", "simulation")

    outer_main_path = root / "main.py"
    outer_main_backup = root / "main.py.batch_rsdql_score_backup"
    outer_main_baseline = outer_main_path.read_text(encoding="utf-8")
    shutil.copy2(outer_main_path, outer_main_backup)

    try:
        for prefix in args.prefixes:
            target_file = root / "data_nbb" / system / "RSDQL" / f"{prefix}user"
            if not target_file.exists():
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text("", encoding="utf-8")

            text = target_file.read_text(encoding="utf-8")
            # 只保留原始内容到首次 run 块之前（避免累积）
            base_lines = trim_existing_runs(text.splitlines())

            # 取最新两条 Actions 行（通常对应 last/best）
            latest_action_lines = extract_latest_two_actions_lines("\n".join(base_lines) if base_lines else text)
            line1, line2 = latest_action_lines[0], latest_action_lines[1]
            actions1 = parse_actions_from_line(line1)
            actions2 = parse_actions_from_line(line2)

            # 同步切外层 main.py 的 metrics 前缀（与你手动一致）
            patched_outer_main = patch_main_metrics_paths(outer_main_baseline, prefix)
            outer_main_path.write_text(patched_outer_main, encoding="utf-8")

            service_graph_path = root / "data" / user / system / run_type / f"{prefix}user_metrics" / "ServiceGraph.csv"
            service_graph = read_service_graph_csv(service_graph_path)

            cc1, ac1, cn1 = calc_costs(service_graph, actions1)
            cc2, ac2, cn2 = calc_costs(service_graph, actions2)

            # 重写文件：保留 base_lines + 追加 run1/run2
            out_lines: list[str] = []
            if base_lines:
                out_lines.extend(base_lines)
                out_lines.append("")  # 空行分隔

            out_lines.append("run1")
            out_lines.append(f"actions_used: {repr(actions1)}")
            out_lines.append(f"cross_cost: {cc1}")
            out_lines.append(f"all_cost: {ac1}")
            out_lines.append(f"cross_num: {cn1}")
            out_lines.append("")
            out_lines.append("run2")
            out_lines.append(f"actions_used: {repr(actions2)}")
            out_lines.append(f"cross_cost: {cc2}")
            out_lines.append(f"all_cost: {ac2}")
            out_lines.append(f"cross_num: {cn2}")
            out_lines.append("")

            target_file.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
            print(f"[完成] 写回 {target_file}")

    finally:
        # 还原外层 main.py
        if outer_main_backup.is_file():
            shutil.copy2(outer_main_backup, outer_main_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())

