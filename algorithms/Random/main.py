import copy
import random
import re
import numpy as np
class myRandom():
    def __init__(self, NodeState, ServiceGraph, ServiceResource, ServiceContainernum):
        # State
        self.NodeResource = NodeState
        self.ServiceGraph = ServiceGraph
        #self.ServiceBaseTime = ServiceBaseTime
        self.ServiceResource = ServiceResource
        self.ServiceContainernum = ServiceContainernum
        self.ResultScore = []
        # 算法函数
        #self.random_steps()
        # 计算函数，把跑出来的日志重新读取，计算cost（对应图4.4、图4.5的响应延迟）
        self.cal_kua()

    def random_steps(self):
        NodeState = self.NodeResource
        for node in NodeState:
            node.append(0)
            node.append(0)
        for index,containerNum in enumerate(self.ServiceContainernum):
            for i in range (containerNum):
                actionl = False
                while not actionl:
                    random_node = random.randint(0,5)
                    if NodeState[random_node][4] + self.ServiceResource[index][0] <= NodeState[random_node][1] and \
                            NodeState[random_node][5] + self.ServiceResource[index][1] <= NodeState[random_node][2]:
                        actionl = True
                        NodeState[random_node][4] = NodeState[random_node][4] + self.ServiceResource[index][0]
                        NodeState[random_node][5] = NodeState[random_node][5] + self.ServiceResource[index][1]
                        print(random_node, index)


        return self.ResultScore


    def cal_kua(self):
        with open('algorithms/Random/log.txt', 'r') as file:
            log_content = file.read()

        # Extract all actions from the log using a regular expression
        actions = re.findall(r'Actions:\[\[(.*?)\]\]', log_content, re.DOTALL)

        # Convert to list of lists of actions (as integers)
        actions = [eval(f'[{action}]') for action in actions]
        # 数组为action对应的索引，一次action是一次部署，一次部署一个pod
        # 单个数组元素为部署策略，格式为[服务索引，节点索引]
        # 服务索引见ServiceResource.csv，节点索引见node.csv
        # 如[4,0]是ServiceResource中索引为4的服务部署在node.csv中索引为0的节点对应的部署策略
        for action in actions:
        #DE = [[4,0],[3,1],[1,2],[4,3],[2,4],[4,5],[2,6],[0,7],[5,8],[3,9]]
        #MB = [[0, 2],  [1, 3], [2, 1], [3, 3], [4, 0] ,[5, 1], [6, 4], [7, 5], [8, 0] ,[9, 0]]
        #RMS = [[4, 3], [7, 0], [8, 2], [3, 2], [2, 2], [0, 0], [5, 2], [9, 4], [6, 0], [1, 0]]
        #RSDQL = [[0,4], [1,4], [5,0] ,[7,5], [9,4] ,[3,5], [4,4] ,[6,5], [8,0] ,[2,5]]
        #RL= [[9, 3], [1, 4], [3, 5], [0, 1], [6, 3], [5, 5], [2, 1], [4, 1], [7, 0], [8, 2]]
            cost = 0
            for container1 in action:
                for index, item in enumerate(self.ServiceGraph):
                    if item != 0:
                        for container2 in action:
                            if container2[0] == index:
                                if not deployw(container1,container2):
                                    cost = cost + self.ServiceGraph[container1[0]][container2[0]]
            print(cost)

# 判断两次部署的服务在不在一个网段，例如[2,4]和[7,4]的2、7服务在不在同一个网段上；0、1；2、3；4、5在同一个网段
def deployw(a,b):
    if a[1] < 2 and b[1] < 2:
        return True
    elif 2<=a[1]<4 and 2<=b[1]<4:
        return True
    elif 4<=a[1]<6 and 4<=b[1]<6:
        return True
    else:
        return False

def get_result(NodeState, ServiceGraph, ServiceResource, ServiceContainernum ):
    myRandom(NodeState, ServiceGraph, ServiceResource, ServiceContainernum)
