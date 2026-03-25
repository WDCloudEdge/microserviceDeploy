import matplotlib.pyplot as plt
import numpy as np

# 1. 基础配置
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.size'] = 11


def plot_icss_style():
    x = [10, 50, 90, 200, 400]
    methods = ["Random", "RL", "RMS_DDPG", "RSDQL"]

    # bookinfo
    data = {
        "Random": [1317.6905990197376, 1182.9375742069797, 1282.018847224882, 1392.2173925471443, 1368.4856945318172],
        "RL": [217.69059901973748, 82.9375742069797, 82.01884722488202, 592.2173925471443, 69.73569453181726],
        "RMS_DDPG": [700, 950, 3200, 4800, 6500],
        "RSDQL": [600, 900, 1800, 2600, 5200],
    }
    data_cross = {
        "Random": [1303.9841629268606, 1177.6358014438233, 1265.639820155887, 1361.2505898056531, 1369.7356945318172],
        "RL": [0, 0, 0, 575.6758211361928, 0],
        "RMS_DDPG": [700, 950, 3200, 4800, 6500],
        "RSDQL": [600, 900, 1800, 2600, 5200],
    }

    # 使用更具质感的学术配色
    colors = ['#2F4F4F', '#4682B4', '#CD853F', '#6B8E23', '#B22222']
    markers = ['o', 'v', '^', 's', 'D']

    fig, ax = plt.subplots(figsize=(6, 4), dpi=300)

    for i, method in enumerate(methods):
        ax.plot(x, data[method], label=method,
                color=colors[i], marker=markers[i],
                markersize=5, linewidth=1.2,
                markerfacecolor='none',  # 空心标志在黑白打印时更有辨识度
                markeredgewidth=1.2)

    # 标签设置
    ax.set_xlabel('User Load', fontdict={'style': 'italic'})  # 有些论文喜欢斜体标签
    ax.set_ylabel('Average Response Latency (ms)')

    # 细节微调
    ax.grid(True, linestyle=':', alpha=0.5)
    ax.legend(loc='best', frameon=True, edgecolor='black', fancybox=False, fontsize=9)

    # 移除上方和右方线条（更现代简洁）
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig('ICSS_Figure.pdf', bbox_inches='tight')  # 强烈建议保存为 PDF
    plt.show()


plot_icss_style()