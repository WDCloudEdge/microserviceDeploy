import copy
import random
import numpy as np
class myRandom():
    def __init__(self, NodeState, ServiceGraph, ServiceResource, ServiceContainernum, ContainerRelationship):
        # State
        self.NodeResource = NodeState
        self.ServiceGraph = ServiceGraph
        #self.ServiceBaseTime = ServiceBaseTime
        self.ServiceResource = ServiceResource
        self.ServiceContainernum = ServiceContainernum
        self.ContainerRelationship = ContainerRelationship
        self.ResultScore = []

    def random_step(self):
        NodeNumber = len(self.NodeResource)
        NodeState = copy.deepcopy(self.NodeResource)
        
        ContainerNumber = 0
        for num in self.ServiceContainernum:
            ContainerNumber += num
        ContainerRelationship = self.ContainerRelationship
        for container, i in enumerate(ContainerRelationship):
            values = [0] * NodeNumber
            cpu = self.ServiceResource[i][0]
            mem =  self.ServiceResource[i][1]
            random_num = random.randint(0, NodeNumber - 1)
            num = 0
            flag = 0
            while num < NodeNumber:
                j = (random_num + num) % NodeNumber
                node_cpu = self.NodeResource[j][1]
                node_mem = self.NodeResource[j][2]
                if node_cpu >= cpu and node_mem >= mem:
                    self.NodeResource[j][1] -= cpu
                    self.NodeResource[j][2] -= mem
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
            NodeState[i][1] = (NodeState[i][1] - self.NodeResource[i][1]) / NodeState[i][1]
            NodeState[i][2] = (NodeState[i][2] - self.NodeResource[i][2]) / NodeState[i][2]
        return self.ResultScore



def get_result(NodeState, ServiceGraph, ServiceResource, ServiceContainernum, ContainerRelationship):
    ran = myRandom(NodeState, ServiceGraph, ServiceResource, ServiceContainernum, ContainerRelationship)
    return ran.random_step()
