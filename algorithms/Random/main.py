import copy
import random
import os
from datetime import datetime
import re
import numpy as np


class myRandom():
    def __init__(self, NodeState, ServiceGraph, ServiceResource, ServiceContainernum):
        # State
        self.NodeResource = NodeState
        self.ServiceGraph = ServiceGraph
        # self.ServiceBaseTime = ServiceBaseTime
        self.ServiceResource = ServiceResource
        self.ServiceContainernum = ServiceContainernum
        self.ResultScore = []

        # 1) 生成本次随机部署策略（仅用于落盘 Actions 日志）
        # deployments = self.random_steps()
        # 2) 计算 cost：保持 cal_kua 内部逻辑不变（仍然从历史 log.txt 读取）;计算函数，把跑出来的日志重新读取，计算cost（对应图4.4、图4.5的响应延迟）
        self.cal_kua()
        # 3) 追加本次运行的 actions 到 algorithms/Random/log.txt
        # self._append_actions_log(deployments)

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
                while True:
                    random_node = random.randint(0, node_num - 1)
                    if NodeState[random_node][4] + self.ServiceResource[service_index][0] <= NodeState[random_node][
                        1] and \
                            NodeState[random_node][5] + self.ServiceResource[service_index][1] <= \
                            NodeState[random_node][2]:
                        NodeState[random_node][4] = NodeState[random_node][4] + self.ServiceResource[service_index][0]
                        NodeState[random_node][5] = NodeState[random_node][5] + self.ServiceResource[service_index][1]
                        deployments.append([service_index, random_node])
                        # 保持原来的输出风格：每次部署打印一次
                        self.x = print('random_node:', random_node, 'service_index:', service_index)
                        break

        return deployments

    def cal_kua(self):
        # 原逻辑：从 algorithms/Random/log.txt 读取历史 Actions，并逐条计算 cost（对应原实现的 cost 输出）
        # with open('algorithms/Random/log.txt', 'r') as file:
        #     log_content = file.read()

        # Extract all actions from the log using a regular expression
        # actions = re.findall(r'Actions:\[\[(.*?)\]\]', log_content, re.DOTALL)

        # Convert to list of lists of actions (as integers)
        # actions = [eval(f'[{action}]') for action in actions]

        # 数组为action对应的索引，一次action是一次部署，一次部署一个pod
        # 单个数组元素为部署策略，格式为[服务索引，节点索引]
        # 服务索引见ServiceResource.csv，节点索引见node.csv
        # 如[4,0]是ServiceResource中索引为4的服务部署在node.csv中索引为0的节点对应的部署策略

        DE = [[0, 5], [1, 4], [2, 0], [3, 0], [4, 1], [5, 0], [6, 3], [7, 5], [8, 2], [9, 0]]
        MB = [[0, 2],  [1, 3], [2, 1], [3, 3], [4, 0] ,[5, 1], [6, 4], [7, 5], [8, 0] ,[9, 0]]
        RMS = [[4, 3], [7, 0], [8, 2], [3, 2], [2, 2], [0, 0], [5, 2], [9, 4], [6, 0], [1, 0]]
        RSDQL = [[0,4], [1,4], [5,0] ,[7,5], [9,4] ,[3,5], [4,4] ,[6,5], [8,0] ,[2,5]]
        RL= [[8, 0], [9, 1], [5, 3], [7, 1], [1, 3], [4, 1], [0, 1], [6, 5], [2, 5], [3, 4]]
        actions = [RL]
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
                                if not deployw(container1, container2):
                                    cross_cost = cross_cost + self.ServiceGraph[container1[0]][container2[0]]
                                    cross_num += 1
                                all_cost = all_cost + self.ServiceGraph[container1[0]][container2[1]]
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


# 判断两次部署的服务在不在一个网段，例如[2,4]和[7,4]的2、7服务在不在同一个网段上；0、1；2、3；4、5在同一个网段
def deployw(a, b):
    if a[1] < 2 and b[1] < 2:
        return True
    elif 2 <= a[1] < 4 and 2 <= b[1] < 4:
        return True
    elif 4 <= a[1] < 6 and 4 <= b[1] < 6:
        return True
    else:
        return False


def get_result(NodeState, ServiceGraph, ServiceResource, ServiceContainernum):
    myRandom(NodeState, ServiceGraph, ServiceResource, ServiceContainernum)
