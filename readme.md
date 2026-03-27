# DRDHR模型算法

本仓库致力于云边协同环境下微服务架构的部署优化研究，主要通过强化学习（RL）算法实现高效的服务调度与资源管理。

## 分支说明

* **`dev_niubingbing`**: 当前主开发分支，默认配置用于运行 **Bookinfo** 数据集。
* **`dev_niubingbing_hipster`**: 专门用于运行 **Hipster** 数据集的分支。

## 环境配置

在运行算法前，请确保 `DRDQL/config.json` 中的参数配置正确：

| 参数 | 说明 |
| :--- | :--- |
| `algorithm` | 当前执行的算法名称。 |
| `system` | 数据集所在的父级文件夹路径。 |
| `user` | 具体数据集文件夹名称（位于 `DQDRL/data/` 目录下）。 |
| `type` | 数据读取模式：`dataset` (从本地数据集读取) 或 `k8s` (从 Kubernetes 集群实时读取)。 |

## 快速开始

1.  **准备数据集**：
    将静态数据集手动放置在 `DQDRL/data/[user]` 目录下。
2.  **修改配置**：
    根据需求编辑 `DRDQL/config.json`。
3.  **运行程序**：
    ```bash
    cd DRDQL
    python main.py
    ```
    
## 实验自动化 (Hyperparameter Tuning)

在 `DRDHR/scripts/` 目录下提供了用于自动化超参数测试的脚本：

* **`batch_rl_beta.py`**: 批量运行不同 **Beta** 值（奖励权重）的实验。
* **`batch_rl_gamma.py`**: 批量运行不同 **Gamma** 值（折扣因子）的实验。

这些脚本会遍历指定的参数范围，自动修改配置并触发训练任务。
```bath
.venv/bin/python scripts/batch_rl_beta.py
.venv/bin/python scripts/batch_rl_gamma.py 
```

## 结果输出与日志

算法运行后的结果将根据算法类型存储在不同位置：

* **本文提出算法 (RL)**：每轮的训练分数（Score）与动作列表（ActionList）记录在根目录的 `log.txt` 中。
* **对比算法**：其他基准算法的结果保存在 `DRDQL/algorithm/[算法名]/log.txt` 中。

## 性能评估 (Cost Calculation)

为了评估算法的实际开销（Cost），请遵循以下步骤：
1.  从对应的 `log.txt` 中提取 `actionList`。
2.  将该动作序列输入到 **Random 算法** 的评估逻辑中进行仿真跑分。
3.  对比不同策略下的最终得分以计算成本差异。


