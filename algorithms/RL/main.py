import numpy as np


class RL():
    def __init__(self, NodeState, ServiceGraph, ServiceBaseTime, ServiceResource, ServiceContainernum,
                 ContainerRelationship):
        # State
        self.NodeResource = NodeState
        self.ServiceGraph = ServiceGraph
        self.ServiceBaseTime = ServiceBaseTime
        self.ServiceResource = ServiceResource
        self.ServiceContainernum = ServiceContainernum
        self.ContainerRelationship = ContainerRelationship
        self.ResultD = []
        self.ResultScore = []

    def random_step(self):
        env = Environment()
        agent = SimpleAgent()
        train_agent(agent, env, episodes=10)
        return 1


def get_result(NodeState, ServiceGraph, ServiceBaseTime, ServiceResource, ServiceContainernum, ContainerRelationship):
    ran = RL(NodeState, ServiceGraph, ServiceBaseTime, ServiceResource, ServiceContainernum,
                   ContainerRelationship)
    return ran.random_step()
