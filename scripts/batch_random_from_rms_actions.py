#!/usr/bin/env python3
"""
批量把 RMS_DDPG 输出文件里的 bestList/lastList 取出来，喂给 Random/main.py 的 RMS 变量，
然后运行项目根目录 main.py（config 里你手动把 algorithm 改成 Random），抓取 Random/main.py 里的
cross_cost/all_cost/cross_num 三个 print，并追加到 data_nbb/<system>/RMS_DDPG/<N>user 文件末尾。

目标文件格式（与现有 data_nbb 仓库风格对齐）：
  data_nbb/<system>/RMS_DDPG/<N>user  （文件本身可能已存在 best/last 结果，脚本会先清掉旧结果）
    - 保留原本 episode:rmsddpg_best / episode:rmsddpg_last 那两行 Actions:...
    - 追加：
        best
        cross_cost: ...
        all_cost: ...
        cross_num: ...
        last
        cross_cost: ...
        all_cost: ...
        cross_num: ...
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


def patch_main_metrics_paths(main_py: str, prefix: int) -> str:
    """
    将项目根目录 main.py 中两处 .../<N>user_metrics/... 精确替换为指定 prefix。
    目标是跟你手动做法一致：第 93 行和第 112 行的 user_metrics 数字同步变化。
    """
    pat_graph = re.compile(
        r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceGraph\.csv['\"])"
    )
    pat_resource = re.compile(
        r"(dataBaseFilePath\s*\+\s*['\"])(\d+)user_metrics/(ServiceResource\.csv['\"])"
    )
    s, n1 = pat_graph.subn(rf"\g<1>{prefix}user_metrics/\3", main_py, count=0)
    s, n2 = pat_resource.subn(rf"\g<1>{prefix}user_metrics/\3", s, count=0)
    if n1 != 1 or n2 != 1:
        raise RuntimeError(
            f"patch_main_metrics_paths failed for prefix={prefix}: "
            f"ServiceGraph matches={n1}, ServiceResource matches={n2}."
        )
    return s


def parse_actions_from_rms_file(text: str, which: str) -> list:
    """
    which: 'best' or 'last' (对应 episode:rmsddpg_best / episode:rmsddpg_last)
    """
    needle = f"episode:rmsddpg_{which}"
    last_actions = None
    for line in text.splitlines():
        if needle in line and "Actions:" in line:
            after = line.split("Actions:", 1)[1].strip()
            # 保险：只截取最外层 [ ... ]
            start = after.find("[")
            end = after.rfind("]")
            if start == -1 or end == -1 or end <= start:
                raise ValueError(f"无法解析 Actions 列表：which={which}, line={line}")
            payload = after[start : end + 1]
            last_actions = ast.literal_eval(payload)
    if last_actions is None:
        raise ValueError(f"在 RMS 文件中找不到 {needle} 行：文件内容可能不符合预期")
    return last_actions


def extract_latest_episode_lines(text: str) -> tuple[str, str]:
    """
    从文件中取最新的 episode:rmsddpg_last 行与 episode:rmsddpg_best 行（保留原整行）。
    返回顺序为 (last_line, best_line)。
    """
    last_line = None
    best_line = None
    for line in text.splitlines():
        if "episode:rmsddpg_last" in line and "Actions:" in line:
            last_line = line.strip()
        elif "episode:rmsddpg_best" in line and "Actions:" in line:
            best_line = line.strip()
    if not last_line or not best_line:
        raise ValueError("RMS 文件中缺少 episode:rmsddpg_last 或 episode:rmsddpg_best 行")
    return last_line, best_line


def parse_actions_from_episode_line(line: str) -> list:
    if "Actions:" not in line:
        raise ValueError(f"该行不包含 Actions: {line}")
    after = line.split("Actions:", 1)[1].strip()
    start = after.find("[")
    end = after.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"无法解析 Actions 列表：line={line}")
    payload = after[start : end + 1]
    return ast.literal_eval(payload)


def trim_existing_best_last_sections(lines: list[str]) -> list[str]:
    """
    旧函数保留（不再使用），避免误操作。
    """
    for i, l in enumerate(lines):
        s = l.strip()
        if s in ("best", "last"):
            return lines[:i]
    return lines


def extract_cross_lines(stdout: str) -> dict:
    """
    从 stdout 里抓三条 print 行。
    返回 dict: {'cross_cost': line, ...}
    """
    cross_cost = None
    all_cost = None
    cross_num = None
    for line in stdout.splitlines():
        if "cross_cost:" in line:
            cross_cost = line.strip()
        elif "all_cost:" in line:
            all_cost = line.strip()
        elif "cross_num:" in line:
            cross_num = line.strip()
    if not (cross_cost and all_cost and cross_num):
        raise RuntimeError(
            "未从 Random 输出中提取到 cross_cost/all_cost/cross_num。"
            f"stdout 前200行：\n{stdout[:2000]}"
        )
    return {"cross_cost": cross_cost, "all_cost": all_cost, "cross_num": cross_num}


def read_service_graph_csv(path: Path) -> list[list[float]]:
    import csv

    with open(path, "r", newline="") as f:
        reader = csv.reader(f)
        next(reader)
        rows = []
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


def patch_random_rms_variable(random_main_text: str, actions: list) -> str:
    """
    替换 algorithms/Random/main.py 中 cal_kua() 里定义的 RMS = ... 这一行。
    假设 RMS 定义在单行里（当前仓库如此）。
    """
    rms_line_pattern = re.compile(r"^(?P<indent>\s*)RMS\s*=.*$", re.MULTILINE)
    replacement = r"\g<indent>RMS = " + repr(actions)
    new_text, n = rms_line_pattern.subn(replacement, random_main_text, count=1)
    if n != 1:
        raise RuntimeError("未能唯一匹配到 Random/main.py 里的 RMS = 赋值行，请检查格式是否被改过。")
    return new_text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prefixes", type=int, nargs="+", default=[10, 50, 90, 200, 400])
    parser.add_argument(
        "--python",
        default=None,
        help="解释器路径（默认使用 .venv/bin/python）",
    )
    parser.add_argument("--no-restore", action="store_true", help="不还原 Random/main.py")
    args = parser.parse_args()

    root = repo_root()
    config_path = root / "config.json"
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    system = cfg.get("system", "bookinfo")

    if args.python:
        py_exe = args.python
    else:
        py_exe = str(root / ".venv" / "bin" / "python")

    random_main_path = root / "algorithms" / "Random" / "main.py"
    if not random_main_path.is_file():
        print(f"找不到 Random/main.py: {random_main_path}", file=sys.stderr)
        return 1

    random_backup = root / "algorithms" / "Random" / "main.py.batch_backup"
    random_text_orig = random_main_path.read_text(encoding="utf-8")
    if not args.no_restore:
        shutil.copy2(random_main_path, random_backup)

    env = os.environ.copy()
    env["DRDQL_SKIP_UVICORN"] = "1"

    outer_main_path = root / "main.py"
    outer_main_backup = root / "main.py.batch_random_backup"
    outer_main_baseline = outer_main_path.read_text(encoding="utf-8")
    shutil.copy2(outer_main_path, outer_main_backup)

    rms_log_prefix_root = root / "data_nbb" / system / "RMS_DDPG"

    try:
        for prefix in args.prefixes:
            rms_file = rms_log_prefix_root / f"{prefix}user"
            if not rms_file.is_file():
                print(f"[跳过] 找不到 RMS 文件：{rms_file}", file=sys.stderr)
                continue

            print(f"\n=== 处理 {prefix}user：{rms_file} ===")
            rms_text = rms_file.read_text(encoding="utf-8")

            # 只保留最新的 episode:rmsddpg_last/best 两行，然后重写文件，
            # 防止历史遗留的多个 episode 行导致解析混乱。
            last_line, best_line = extract_latest_episode_lines(rms_text)
            # 保持文件中“出现顺序”，并且后续不再区分 best/last，只按两条 Actions 依次跑两次
            ordered_episode_lines = [last_line, best_line]
            if rms_text.find(best_line) < rms_text.find(last_line):
                ordered_episode_lines = [best_line, last_line]
            rms_file.write_text("\n".join(ordered_episode_lines) + "\n", encoding="utf-8")

            # 关键：同步把外层 main.py 的 user_metrics 切到当前 prefix（与你手动改 93/112 行一致）
            patched_outer_main = patch_main_metrics_paths(outer_main_baseline, prefix)
            outer_main_path.write_text(patched_outer_main, encoding="utf-8")

            # 读取本轮 ServiceGraph，用于“自校验/兜底计算”
            service_graph_path = root / "data" / cfg.get("user", "nbb") / system / cfg.get("type", "simulation") / f"{prefix}user_metrics" / "ServiceGraph.csv"
            service_graph = read_service_graph_csv(service_graph_path)

            # 不再区分 best/last：按两条 episode 行的顺序取出两个数组分别跑
            run_inputs = [
                ("run1", ordered_episode_lines[0]),
                ("run2", ordered_episode_lines[1]),
            ]
            for tag, ep_line in run_inputs:
                actions = parse_actions_from_episode_line(ep_line)
                patched = patch_random_rms_variable(random_text_orig, actions)
                random_main_path.write_text(patched, encoding="utf-8")

                proc = subprocess.run(
                    [py_exe, str(outer_main_path)],
                    cwd=str(root),
                    env=env,
                    capture_output=True,
                    text=True,
                )
                out = (proc.stdout or "") + (proc.stderr or "")
                if proc.returncode != 0:
                    raise RuntimeError(
                        f"运行 main.py 失败：prefix={prefix}, {tag}, rc={proc.returncode}\n输出：\n{out[-4000:]}"
                    )

                cross = extract_cross_lines(out)
                # 用同一套公式直接复算一遍，若 stdout 提取值不一致，用复算值替代并标记
                cc, ac, cn = calc_costs(service_graph, actions)
                # stdout 解析出来的是字符串，如 'cross_cost: 123.4'
                def _num(s: str) -> float:
                    return float(s.split(":", 1)[1].strip())

                mismatch = False
                try:
                    mismatch = (
                        abs(_num(cross["cross_cost"]) - cc) > 1e-6
                        or abs(_num(cross["all_cost"]) - ac) > 1e-6
                        or int(float(cross["cross_num"].split(":", 1)[1].strip())) != int(cn)
                    )
                except Exception:
                    mismatch = True

                if mismatch:
                    cross = {
                        "cross_cost": f"cross_cost: {cc}",
                        "all_cost": f"all_cost: {ac}",
                        "cross_num": f"cross_num: {cn}",
                    }
                    cross["_note"] = "note: stdout mismatch, used recomputed values"
                with open(rms_file, "a", encoding="utf-8") as f:
                    f.write(f"\n{tag}\n")
                    f.write(f"actions_used: {repr(actions)}\n")
                    if "_note" in cross:
                        f.write(cross["_note"] + "\n")
                    f.write(cross["cross_cost"] + "\n")
                    f.write(cross["all_cost"] + "\n")
                    f.write(cross["cross_num"] + "\n")

            print(f"[完成] {rms_file}")
    finally:
        # 无论成功失败，都还原外层 main.py
        if outer_main_backup.is_file():
            shutil.copy2(outer_main_backup, outer_main_path)

    if not args.no_restore and random_backup.is_file():
        shutil.copy2(random_backup, random_main_path)
        print(f"\n已还原 Random/main.py（来自 {random_backup}）")

    return 0


if __name__ == "__main__":
    sys.exit(main())

