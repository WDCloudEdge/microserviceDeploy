import random
import numpy as np
import csv
import pandas as pd
import time

def remove_first_row(file_path):
    outfile = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            outfile.append(row)  # 去掉第一列并转换为浮点数
    return outfile

def remove_first_row_column(file_path):
    outfile = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            outfile.append([float(value) for value in row[1:]])  # 去掉第一列并转换为浮点数
    return outfile

class myRandom():
    def __init__(self, NodeState, ServiceResource):
        # State
        self.NodeResource = NodeState
        self.ServiceResource = ServiceResource
        self.ResultD = []
        self.ResultScore = []

    def random_step(self):
        NodeNumber = len(self.NodeResource)
        NodeState = np.copy(self.NodeResource)
        for i, container in enumerate(self.ServiceResource):
            values = [0] * NodeNumber
            cpu = float(container[1])
            mem =  float(container[2])
            random_num = random.randint(0, NodeNumber - 1)
            num = 0
            flag = 0
            while num < NodeNumber:
                j = (random_num + num) % NodeNumber
                node_cpu = self.NodeResource[j][0]
                node_mem = self.NodeResource[j][1]
                if node_cpu >= cpu and node_mem >= mem:
                    self.NodeResource[j][0] -= cpu
                    self.NodeResource[j][1] -= mem
                    self.ResultD.append([j, i])
                    values[j] = 100
                    self.ResultScore.append(values)
                    # print(f"Service {i} placed on Node {j}")
                    flag = 1
                    break
                else:
                    num = num + 1
            if flag != 1:
                print(f"Service {i} Container {container} can't place on any node.")
        #NodeState为节点资源利用率
        for i in range(len(NodeState)):
            NodeState[i][0] = (NodeState[i][0] - self.NodeResource[i][0]) / NodeState[i][0]
            NodeState[i][1] = (NodeState[i][1] - self.NodeResource[i][1]) / NodeState[i][1]
        return self.ResultD, self.ResultScore, NodeState


NodeStates = remove_first_row_column(r'E:\research\my_deployment\data\wcx\hipster\simulation\node.csv')
ServiceResource = remove_first_row(r'E:\research\my_deployment\data\wcx\hipster\simulation\ServiceResource.csv')
myRandom = myRandom(NodeStates, ServiceResource)
sorted_data, _, _ = myRandom.random_step()
result_df = pd.read_csv(r'E:\research\my_deployment\placement\service.csv', header=None)
df = pd.DataFrame(sorted_data, columns=[0, 1])
mapping = {2: 'izn4afyfnvcx9i7ztdrlcoz', 0: 'server-1', 1: 'server-2'}
df['result'] = df[0].map(mapping)
result_df['result'] = df['result']
timestamp = str(int(time.time()))
al_name = 'Random'
file_path = rf'E:\research\my_deployment\placement\service&placement_{al_name}_{timestamp}.csv'
result_df.to_csv(file_path, index=False)
