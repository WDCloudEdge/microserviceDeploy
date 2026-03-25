import copy
import random
import os
from datetime import datetime
import re
import numpy as np

node_map = {
    "node-5": 0,
    "node-7": 1,
    "node-219": 2,
    "node-221": 3,
    # "node-218": 4,
    "node-6": 4,
    "node-227": 5,
}

index_service_map = {
    0: "details-v1",
    1: "productpage-v1",
    2: "ratings-v1",
    3: "reviews-v1",
    4: "reviews-v2",
    5: "reviews-v3",
}

class myRandom():
    def __init__(self, NodeState, ServiceGraph, ServiceResource, ServiceContainernum, graph):
        # State
        self.NodeResource = NodeState
        self.ServiceGraph = ServiceGraph
        # self.ServiceBaseTime = ServiceBaseTime
        self.ServiceResource = ServiceResource
        self.ServiceContainernum = ServiceContainernum
        self.ResultScore = []
        self.graph = graph

        # 1) 生成本次随机部署策略（仅用于落盘 Actions 日志）
        # deployments = self.random_steps()
        # 2) 追加本次运行的 actions 到 algorithms/Random/log.txt
        # self._append_actions_log(deployments)
        # 3) 计算 cost：保持 cal_kua 内部逻辑不变（仍然从历史 log.txt 读取）;计算函数，把跑出来的日志重新读取，计算cost（对应图4.4、图4.5的响应延迟）
        self.cal_kua()

    def random_steps(self):
        # 深拷贝，避免污染主程序传入的 NodeState
        NodeState = copy.deepcopy(self.NodeResource)
        for node in NodeState:
            node.append(0)
            node.append(0)
        deployments = []  # [[服务索引, 节点索引], ...]
        node_num = len(NodeState)

        for service_index, containerNum in enumerate(self.ServiceContainernum):
            for _ in range(containerNum):
                # 避免 while True 卡死：每个实例最多尝试固定次数
                max_attempts = max(100, node_num * 20)
                placed = False
                for _attempt in range(max_attempts):
                    random_node = random.randint(0, node_num - 1)
                    if NodeState[random_node][4] + self.ServiceResource[service_index][0] <= NodeState[random_node][
                        1] and \
                            NodeState[random_node][5] + self.ServiceResource[service_index][1] <= \
                            NodeState[random_node][2]:
                        NodeState[random_node][4] = NodeState[random_node][4] + self.ServiceResource[service_index][0]
                        NodeState[random_node][5] = NodeState[random_node][5] + self.ServiceResource[service_index][1]
                        deployments.append([service_index, random_node])
                        # 保持原来的输出风格：每次部署打印一次
                        print('random_node:', random_node, 'service_index:', service_index)
                        placed = True
                        break
                if not placed:
                    raise RuntimeError(
                        f"Random placement failed after {max_attempts} attempts: "
                        f"service_index={service_index}, req_cpu={self.ServiceResource[service_index][0]}, "
                        f"req_mem={self.ServiceResource[service_index][1]}. "
                        f"Please check NodeState columns and resource feasibility."
                    )

        return deployments

    def cal_kua(self):
        # 原逻辑：从 algorithms/Random/log.txt 读取历史 Actions，并逐条计算 cost（对应原实现的 cost 输出）
        # with open('algorithms/Random/log.txt', 'r') as file:
        #     log_content = file.read()
        #
        # # Extract all actions from the log using a regular expression
        # actions = re.findall(r'Actions:\[\[(.*?)\]\]', log_content, re.DOTALL)
        #
        # # Convert to list of lists of actions (as integers)
        # actions = [eval(f'[{action}]') for action in actions]

        # 数组为action对应的索引，一次action是一次部署，一次部署一个pod
        # 单个数组元素为部署策略，格式为[服务索引，节点索引]
        # 服务索引见ServiceResource.csv，节点索引见node.csv
        # 如[4,0]是ServiceResource中索引为4的服务部署在node.csv中索引为0的节点对应的部署策略

        # DE = [[0, 1], [1, 5], [2, 0], [3, 0], [4, 2], [5, 5], [6, 4], [7, 3], [8, 4], [9, 4]]
        MB = [[0, 2], [1, 3], [2, 1], [3, 3], [4, 0], [5, 1], [6, 4], [7, 5], [8, 0], [9, 0]]
        RMS = [[3, 2], [2, 2], [5, 3], [1, 2], [4, 2], [0, 2]]
        RSDQL = [[0, 4], [1, 4], [5, 0], [7, 5], [9, 4], [3, 5], [4, 4], [6, 5], [8, 0], [2, 5]]
        # RL = [[1, 5], [4, 4], [0, 4], [2, 4], [3, 4], [5, 5]]

        # actions = [actions[len(actions) - 1]]
        actions = [RMS]
        for action in actions:
            # 跨网段的服务部署策略延迟
            cross_cost = 0
            # 所有的服务部署策略延迟
            all_cost = 0
            # 跨网段服务数量
            cross_num = 0
            for container1 in action:
                for index, item in enumerate(self.ServiceGraph):
                    if item != 0:
                        for container2 in action:
                            if container2[0] == index:
                                # deployyw()用来判断两个[][]是否跨网段

                                # TODO 计算总延迟需要根据graph算上权重，先固定权重0.9875
                                # 之前在graph中已经跨网段的延迟如果部署之后没有跨网段需要乘上1-权重，仍然跨网段保留原值
                                # 之前在graph中没有跨网段的延迟如果部署之后没有跨网段保留原值，跨网段需要除以1-权重
                                old_container1_node_index = node_map[self.graph[index_service_map[container1[0]]]]
                                old_container2_node_index = node_map[self.graph[index_service_map[container2[0]]]]
                                new_container1_node_index = container1[1]
                                new_container2_node_index = container2[1]

                                if not deployw(container1[1], container2[1]) and self.ServiceGraph[container1[0]][
                                    container2[0]] != 0:
                                    cross_num += 1

                                a = 50
                                # 如果之前的没有跨网段
                                if deployw(old_container1_node_index, old_container2_node_index):
                                    # 如果现在的没有跨网段
                                    if deployw(new_container1_node_index, new_container2_node_index):
                                        all_cost += self.ServiceGraph[container1[0]][container2[0]]
                                    else:
                                        all_cost += self.ServiceGraph[container1[0]][container2[0]] + a
                                        cross_cost += self.ServiceGraph[container1[0]][container2[0]] + a
                                # 如果之前的有跨网段
                                else:
                                    # 如果现在的没有跨网段
                                    if deployw(new_container1_node_index, new_container2_node_index):
                                        all_cost += max((self.ServiceGraph[container1[0]][container2[0]] - a), 1)
                                    else:
                                        all_cost += self.ServiceGraph[container1[0]][container2[0]]
                                        cross_cost += self.ServiceGraph[container1[0]][container2[0]]
                                print('all_cost', all_cost)
            print('cross_cost:', cross_cost)
            print('all_cost:', all_cost)
            print('cross_num:', cross_num)

    def _append_actions_log(self, deployments):
        log_path = os.path.join(os.path.dirname(__file__), 'log.txt')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]

        # 让格式尽量贴近原来 log.txt：... Actions:[[4, 5], [1, 2], ...]
        actions_str = str(deployments)
        line = f"{timestamp} - INFO - episode:runtime totalReward:-1 Actions:{actions_str}\n"
        # 如果文件最后一行没有以换行符结尾，新写入会直接拼接到上一行。
        # 这里在写入前检查最后一个字节，必要时先补一个 '\n'。
        last_byte = None
        try:
            with open(log_path, 'rb') as fb:
                fb.seek(-1, os.SEEK_END)
                last_byte = fb.read(1)
        except OSError:
            # 文件为空时直接写入即可
            last_byte = None

        with open(log_path, 'a') as f:
            if last_byte not in (b'\n', None):
                f.write('\n')
            f.write(line)

# 网段1
# node-5: 0 node-7: 1
# 网段2
# node-219: 2 node-221: 3
# 网段3
# node-6: 4
# 网段4
# node-227: 5
# 判断两次部署的服务在不在一个网段，例如[2,4]和[7,4]的2、7服务在不在同一个网段上；0、1；2、3；4、5在同一个网段
def deployw(a, b):
    if a < 2 and b < 2:
        return True
    elif 2 <= a < 4 and 2 <= b < 4:
        return True
    elif 4 == a and 4 == b:
        return True
    elif 5 == a and 5 == b:
        return True
    else:
        return False


def get_result(NodeState, ServiceGraph, ServiceResource, ServiceContainernum, graph):
    myRandom(NodeState, ServiceGraph, ServiceResource, ServiceContainernum, graph)
