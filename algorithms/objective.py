import numpy as np



class Objective:
    def __init__(self, Latency):
        self.Latency = Latency
        self.Efficiency = 0
    
    def set_efficiency(self, Efficiency):
        self.Efficiency = Efficiency

    def get_reward(self):
        return self.Latency


def get_objective(NodeState, ServiceGraph, ServiceBaseTime, ServiceContainernum, ContainerRelationship, ResultD):
    '''
    NodeState,大小为n×3,为每个节点cpu和mem使用率以及所在网段,如NodeState[i][0]=50为第i个节点的cpu使用率为50%
    ServiceGraph为微服务间跨服务器的通信时间,为对称矩阵
    ServiceBaseTime为每个微服务运行的时间,ServiceBaseTime[i]=200,表示服务i的运行时间是200ms
    ResultD为每个微服务部署的节点,ResultD[i]=1,表示容器i部署在节点1上
    '''
    CommunTime = 0
    for i in range ( len(ContainerRelationship) ):
         for j in range ( len(ContainerRelationship) ):
              k = ContainerRelationship[i]
              l = ContainerRelationship[j]
              CommunTimeInContainers = ServiceGraph[k][l] / (ServiceContainernum[k] * ServiceContainernum[l])
              CommunTime += CommunTimeInContainers * (NodeState[ResultD[i]][2] == NodeState[ResultD[j]][2])
    return Objective(CommunTime)
