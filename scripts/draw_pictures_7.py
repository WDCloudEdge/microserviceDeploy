import matplotlib.pyplot as plt
import numpy as np
import re


def set_academic_style():
    """设置符合学术论文要求的绘图格式"""
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman']
    plt.rcParams['mathtext.fontset'] = 'stix'  # 让数学公式更接近 LaTeX 风格
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['legend.fontsize'] = 10
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'
    plt.rcParams['axes.axisbelow'] = True  # 网格线置于底层


def exponential_moving_average(data, weight=0.9):
    """指数移动平均平滑，修复了 NumPy 逻辑判断歧义"""
    if len(data) == 0:
        return np.array([])
    smoothed = [data[0]]
    for point in data[1:]:
        val = smoothed[-1] * weight + (1 - weight) * point
        smoothed.append(val)
    return np.array(smoothed)


def parse_log(file_path):
    """从日志中提取 episode 和 reward"""
    episodes, rewards = [], []
    pattern = re.compile(r"episode:(\d+)\s+totalReward:([\d.]+)")

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                reward_val = float(match.group(2))
                if reward_val == 0:
                    continue  # 发现 0，直接跳过这一行，不执行后面的 append
                episodes.append(int(match.group(1)))
                rewards.append(float(match.group(2)))
    return np.array(episodes), np.array(rewards)


def plot_comparison(logs_dict, weight=0.9):
    set_academic_style()
    fig, ax = plt.subplots(figsize=(7, 4.5), dpi=300)

    # 定义学术常用配色方案
    colors = ['#E41A1C', '#377EB8', '#4DAF4A', '#984EA3', '#FF7F00']

    for i, (label, path) in enumerate(logs_dict.items()):
        try:
            ep, rw = parse_log(path)
            if len(rw) == 0: continue

            # 平滑处理
            smooth_rw = exponential_moving_average(rw, weight=weight)
            color = colors[i % len(colors)]

            # 绘制原始数据（浅色细线）
            ax.plot(ep, rw, color=color, alpha=0.15, linewidth=0.6)
            # 绘制平滑数据（主线）
            ax.plot(ep, smooth_rw, color=color, linewidth=1.8, label=label)

        except Exception as e:
            print(f"处理 {label} 时出错: {e}")

    # 细节修饰
    ax.set_xlabel('Training Episodes')
    ax.set_ylabel('Total Reward Value')
    ax.grid(True, linestyle='--', alpha=0.5)

    # 强制从 0 开始
    ax.set_xlim(left=0)

    # 图例设置：去边框或细边框，置于合适位置
    ax.legend(loc='best', frameon=True, edgecolor='gray', framealpha=0.8)

    plt.tight_layout()
    plt.savefig('comparison_result.pdf', bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    # --- 在这里配置你的日志文件 ---
    logs_to_plot = {
        'Proposed DRDQL': 'train_drdql.log',  # 你的新算法
        'Baseline (DDPG)': 'train_ddpg.log'  # 对比算法
    }

    plot_comparison(logs_to_plot, weight=0.92)