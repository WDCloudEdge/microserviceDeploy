import matplotlib.pyplot as plt

# 1. 基础配置
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']
plt.rcParams['mathtext.fontset'] = 'stix'
plt.rcParams['font.size'] = 14


def calculate_difference_percentage(list1, list2):
    """
    计算 (sum(list1 - list2) / sum(list1)) * 100
    """
    if not list1:
        return 0

    sum1 = sum(list1)
    sum2 = sum(list2)

    # 计算差值的总和
    total_diff = sum1 - sum2

    # 计算百分比
    percentage = (total_diff / sum1) * 100
    return percentage


# 你的数据
rms_ddpg =[69.73569453181726, 82.01884722488202, 217.69059901973748, 592.2173925471443, 882.9375742069797]
drdhr = [69.73569453181726, 82.9375742069797, 82.01884722488202, 217.69059901973748, 592.2173925471443]


result = calculate_difference_percentage(rms_ddpg, drdhr)
print(f"计算结果为: {result:.2f}%")


def plot_icss_style():
    x = [10, 50, 90, 200, 400]
    methods = ["Default", "RMS_DDPG", "RSDQL", "DRDHR", "DRDHR-w"]

    # bookinfo
    data = {
        "Default": [1182.9375742069797, 1282.018847224882, 1317.6905990197376, 1368.4856945318172, 1392.2173925471443],
        "RMS_DDPG": [582, 717, 869.7356945318173, 1182, 1192],
        "RSDQL": [582.9375742069797, 582.018847224882, 592.2173925471442, 569.7356945318172, 717.6905990197374],
        "DRDHR": [69.73569453181726, 82.9375742069797, 82.01884722488202, 217.69059901973748, 592.2173925471443],
        "DRDHR-w": [69.73569453181726, 82.01884722488202, 217.69059901973748, 592.2173925471443, 882.9375742069797]
    }
    data_cross = {
        "Default": [1177.6358014438233, 1265.639820155887, 1303.9841629268606, 1361.2505898056531, 1369.7356945318172],
        "RMS_DDPG": [511.7182606117371, 689.6800060181954, 842.0671533422059, 1149.0647042758474, 1168.8827201544407],
        "RSDQL": [562.1316376464587, 563.1403096328519, 575.6758211361928, 689.6800060181954, 812.7359475754313],
        "DRDHR": [0, 0, 0, 0, 575.6758211361928],
        "DRDHR-w": [0, 0, 0, 575.6758211361928, 856.8298648833022]
    }
    # hipster
    # data = {
    #     "Default": [4081.769822626804, 4187.6189411011, 4438.7539049860225, 7014.109226803007, 12844.57375035587],
    #     "RMS_DDPG": [3601.2538475217825, 3668.6620318167415, 4465.965483891698, 6959.109226803006, 12797.57375035587],
    #     "RSDQL": [3861.693502694196, 4111.662031816742, 4536.7539049860225, 7061.109226803007, 12946.57375035587],
    #     "DRDHR-w": [3414.6935026941965, 3566.6620318167415, 4042.7539049860234, 6567.109226803006, 12652.57375035587],
    #     "DRDHR": [2651.22233758881, 2899.140346875999, 3405.2986345315876, 5926.109226803006, 11811.57375035587]
    # }
    # data_cross = {
    #     "Default": [4071.769822626804, 3912.464880551273, 4305.607627320632, 7004.109226803007, 12692.68612169693],
    #     "RSDQL": [3005.53813067661, 3149.6876591980636, 3642.7246178169803, 5775.7439391919315, 12080.740735052334],
    #     "RMS_DDPG": [2448.8547870480556, 2555.1115906315517, 4039.581954928448, 6126.880042095016, 11624.411900656902],
    #     "DRDHR-w": [3432.263159190576, 2921.4461669011334, 3613.888668185976, 4436.879037802018, 11812.099920925017],
    #     "DRDHR": [2139.6679179521752, 2318.8129589168448, 2693.7530390524507, 4688.344533015123, 10102.46120919602]
    # }

    # 使用更具质感的学术配色
    colors = ['#2F4F4F', '#4682B4', '#CD853F', '#B22222', '#6B8E23']
    markers = ['o', 'o', 'o', 'o', 'D']

    # 调矮整体高度，给图例留少量空间
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(12, 3.7), dpi=300, sharey=False)

    for i, method in enumerate(methods):
        ax_a.plot(x, data[method], label=method,
                  color=colors[i], marker=markers[i],
                  markersize=5, linewidth=1.2,
                  markerfacecolor='none',
                  markeredgewidth=1.2)
        ax_b.plot(x, data_cross[method], label='_nolegend_',
                  color=colors[i], marker=markers[i],
                  markersize=5, linewidth=1.2,
                  markerfacecolor='none',
                  markeredgewidth=1.2)

    for ax in (ax_a, ax_b):
        ax.set_xlabel('User Load')
        ax.set_xticks(x)
        ax.grid(True, linestyle=':', alpha=0.5)
        # 坐标系边框画成完整长方形（右上角封口）
        ax.spines['top'].set_visible(True)
        ax.spines['right'].set_visible(True)

    ax_a.set_ylabel('Average Service Latency (ms)')
    ax_b.set_ylabel('Cross-segment Service Latency (ms)')

    # 子图标题（可按论文需要改文案）
    ax_a.set_title('(a) Average service latency')
    ax_b.set_title('(b) Cross-segment latency')

    # 共用图例：只从左图取 handles/labels，放在整图下方居中
    handles, labels = ax_a.get_legend_handles_labels()
    fig.legend(
        handles, labels,
        # 图例贴近坐标系下方，减少底部留白
        loc='lower center',
        bbox_to_anchor=(0.0, 0.02, 1.0, 0.0),
        ncol=len(methods),
        mode="expand",
        frameon=True,
        edgecolor='black',
        fancybox=False,
        fontsize=9,
    )

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    plt.savefig('bookinfo_service_latency.pdf', bbox_inches='tight')
    plt.show()


# plot_icss_style()
