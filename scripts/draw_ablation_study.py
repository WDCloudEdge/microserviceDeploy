import matplotlib.pyplot as plt
import numpy as np

# 1. 基础配置
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.size'] = 12


def plot_ablation_final_refined():
    # 负载横坐标
    x_labels = ['10', '50', '90', '200', '400']
    x = np.arange(len(x_labels))
    width = 0.35

    # --- 数据准备 ---
    bi_drdhr_w = [69.73569453181726, 82.01884722488202, 217.69059901973748, 592.2173925471443, 882.9375742069797]
    bi_drdhr = [69.73569453181726, 82.9375742069797, 82.01884722488202, 217.69059901973748, 592.2173925471443]

    ob_drdhr_w = [3414.6935026941965, 3566.6620318167415, 4042.7539049860234, 6567.109226803006, 12652.57375035587]
    ob_drdhr = [2651.22233758881, 2899.140346875999, 3405.2986345315876, 5926.109226803006, 11811.57375035587]

    # 参考图配色
    color_w = '#4682B4'  # 蓝色
    color_full = '#CD5C5C'  # 红色

    # 增加 figsize 的高度，为底部标题留出更多空间
    fig, (ax_bi, ax_ob) = plt.subplots(1, 2, figsize=(12, 5), dpi=300)

    def draw_subplot(ax, data_w, data_full, title):
        # 绘制柱状图
        rects1 = ax.bar(x - width / 2, data_w, width, label='DRDHR-w',
                        color=color_w, edgecolor='black', linewidth=1.5, hatch='//')
        rects2 = ax.bar(x + width / 2, data_full, width, label='DRDHR',
                        color=color_full, edgecolor='black', linewidth=1.5, hatch='xx')

        # 修正重叠：将 title (a/b) 的 y 轴位置向下进一步移动，或者使用 xlabel 拼接
        ax.set_xlabel('User Load\n' + title, fontweight='bold', fontsize=14, labelpad=2)
        ax.set_ylabel('Average Service Latency (ms)', fontweight='bold')

        ax.set_xticks(x)
        ax.set_xticklabels(x_labels)

        # 坐标轴加粗
        for spine in ax.spines.values():
            spine.set_linewidth(1.5)

        # 网格线
        ax.grid(axis='y', linestyle='--', alpha=0.7)

        # 1. 给所有的柱子加上数值标注
        # 2. 调整标注位置 (va='bottom', 并增加空隙) 避免与边框重合
        def autolabel(rects):
            for rect in rects:
                height = rect.get_height()
                ax.annotate(f'{height:.0f}',
                            xy=(rect.get_x() + rect.get_width() / 2, height),
                            xytext=(0, 3),  # 向上偏移 3 points
                            textcoords="offset points",
                            ha='center', va='bottom', fontsize=9)

        autolabel(rects1)
        autolabel(rects2)

        # 稍微拉高 y 轴上限，防止最高处的数值标到框外
        ax.set_ylim(0, max(max(data_w), max(data_full)) * 1.15)

    draw_subplot(ax_bi, bi_drdhr_w, bi_drdhr, '(a) BI Dataset')
    draw_subplot(ax_ob, ob_drdhr_w, ob_drdhr, '(b) OB Dataset')

    # --- 修正图例 ---
    handles, labels = ax_bi.get_legend_handles_labels()
    fig.legend(handles, labels, loc='upper center',
               bbox_to_anchor=(0.5, 0.95),
               ncol=2, frameon=False, fontsize=13, columnspacing=8)

    # 调整整体布局：增加 bottom 留白，增加 top 留白
    plt.tight_layout(rect=[0, 0.05, 1, 0.91])

    plt.savefig('ablation_study.pdf', bbox_inches='tight')
    plt.show()


if __name__ == "__main__":
    plot_ablation_final_refined()