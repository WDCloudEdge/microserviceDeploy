import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns


def set_professional_style():
    # --- 核心设置：Times New Roman ---
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman'] + plt.rcParams['font.serif']
    plt.rcParams['mathtext.fontset'] = 'stix'  # 公式也用 Times 风格

    # --- 其他细节 ---
    plt.rcParams['font.size'] = 11
    plt.rcParams['axes.labelsize'] = 12
    plt.rcParams['xtick.labelsize'] = 11
    plt.rcParams['ytick.labelsize'] = 11
    plt.rcParams['legend.fontsize'] = 10

    plt.rcParams['xtick.direction'] = 'in'  # 刻度向内
    plt.rcParams['ytick.direction'] = 'in'  # 刻度向内
    plt.rcParams['axes.linewidth'] = 1.0  # 边框粗细


def plot_boxplot_distribution(csv_file=None):
    """
    绘制延迟分布箱线图。
    如果 csv_file 为空，则使用模拟数据。
    """
    set_professional_style()

    # === 1. 数据准备 (如果是真实数据，这里应读取 CSV) ===
    # 模拟 5 种算法的数据分布
    np.random.seed(123)
    methods = ["Default", "MB_DDPG", "RMS_DDPG", "RSDQL", "DRDQL"]

    # 构造 Bookinfo 数据 (延迟在 400-1000ms 之间)
    data_bookinfo = [np.random.normal(mu, sigma, 100) for mu, sigma in
                     zip([800, 780, 750, 650, 600], [100, 90, 80, 110, 70])]

    # === 2. 绘图设置 ===
    # 使用稳重的学术配色
    palette = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00']

    # 创建画布 (1 行 2 列，这里先写单列示例)
    fig, ax = plt.subplots(figsize=(6, 4.5), dpi=300)

    # === 3. 绘制箱线图 ===
    # 使用 Seaborn 绘制基础箱线
    sns.boxplot(data=data_bookinfo,
                palette=palette,
                width=0.4,  # 箱体宽度
                linewidth=1.2,  # 线条粗细
                fliersize=3,  # 异常点大小
                showmeans=True,  # 显示均值
                # 均值用空心圆圈表示，打印更清晰
                meanprops={"marker": "o", "markerfacecolor": "none", "markeredgecolor": "black", "markersize": "6"},
                ax=ax)

    # === 4. 细节调整 ===
    # X 轴标签
    ax.set_xticks(range(len(methods)))
    ax.set_xticklabels(methods)

    # 标签和标题 (ICSS 通常要求英文)
    ax.set_xlabel('Algorithms')
    ax.set_ylabel('Request Latency (ms)')
    # ax.set_title('(a) Bookinfo Scenario') # 如果需要子图标题

    # 优化网格线
    ax.grid(axis='y', linestyle=':', color='gray', alpha=0.5)

    # Despine: 去掉上边框和右边框，减少干扰
    sns.despine()

    # === 5. 保存图表 ===
    plt.tight_layout()
    # 强烈建议保存为 PDF
    plt.savefig('fig_latency_boxplot_distribution.pdf', bbox_inches='tight')
    plt.show()


# 运行绘图
plot_boxplot_distribution()