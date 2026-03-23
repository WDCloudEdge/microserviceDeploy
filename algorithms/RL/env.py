beta = [0.8, 0.2]
alpha = 0.8
max_temp = 0
import numpy as np
import math
import itertools
import copy


class Env():
    def __init__(self, nodeState, ServiceGraph, ServiceResource, ServiceContainernum):
        # State
        self.State = []
        self.service_graph = ServiceGraph
        self.action_queue = []
        self.node_state_queue = []
        self.node_state = nodeState
        self.container_state_queue = []
        self.service_resource = ServiceResource
        self.service_container_num = ServiceContainernum
        self.prepare()
        self.all_reward = []

    def if_valid_action(self, action):
        if (self.container_state_queue[action[0]][0] == -1) & (self.node_state_queue[action[1]][1] >= (
                self.node_state_queue[action[1]][4] + self.container_state_queue[action[0]][2])) & (
                self.node_state_queue[action[1]][2] >= (
                self.node_state_queue[action[1]][5] + self.container_state_queue[action[0]][3])):
            return True
        else:
            return False

    def if_invalid_state(self, agent):
        # q_values = agent.q_table[agent.state_to_index(self.State)]
        # if all(value == -1000 for value in q_values):
        #     return True
        # else:
        #     return False
        state_invalid = True
        for i in range(agent.act_dim):
            if self.if_valid_action(self.index_to_act(i)):
                state_invalid = False
        return state_invalid

    def prepare(self):
        self.container_state_queue = []
        self.action_queue = []
        self.node_state_queue = copy.deepcopy(self.node_state)
        for index, containernum in enumerate(self.service_container_num):
            for i in range(containernum):
                container_state = [-1, index + 1, self.service_resource[index][0], self.service_resource[index][1]]
                self.container_state_queue.append(container_state)
        for row in self.node_state_queue:
            row.extend([0, 0])
        self.State = list(itertools.chain.from_iterable(self.container_state_queue + self.node_state_queue))

    # def CalcuCost(self, action):
    #     total = 0
    #     for container_graph in self.service_graph:
    #         temp_total = 0
    #         for a in container_graph:
    #             temp_total += a
    #             if temp_total > total:
    #                 total = temp_total
    #     cost = 0
    #     # for container1 in self.container_state_queue:
    #     container1 = self.container_state_queue[action[0]]
    #     if container1[0] != -1:
    #         container_graph = self.service_graph[container1[1] - 1]
    #         for index, item in enumerate(container_graph):
    #             if item != 0:
    #                 for container2 in self.container_state_queue:
    #                     if container2[1] - 1 == index:
    #                         if (container2[0] != -1) and not (self.deployw(container1,container2)):
    #                             cost = cost + container_graph[container2[1] - 1]
    #     return cost * 20

    def CalcuCost2(self, action):
        de = 0
        # for container1 in self.container_state_queue:
        container1 = self.container_state_queue[action[0]]
        if container1[0] != -1:
            container_graph = self.service_graph[container1[1] - 1]
            for index, item in enumerate(container_graph):
                if item != 0:
                    for container2 in self.container_state_queue:
                        if container2[1] - 1 == index:
                            if (container2[0] != -1) and (self.deployw(container1,container2)):
                                de = de + container_graph[container2[1] - 1]
                            if (container2[0] != -1) and not (self.deployw(container1, container2)):
                                de = de - container_graph[container2[1] - 1]
        return de*3

    def CalcuAllCost(self):
        total = 0
        for container_graph in self.service_graph:
            for a in container_graph:
                total += a
        cost = 0
        for container1 in self.container_state_queue:
            # container1 = self.container_state_queue[action[0]]
            if container1[0] != -1:
                container_graph = self.service_graph[container1[1] - 1]
                for index, item in enumerate(container_graph):
                    if item != 0:
                        for container2 in self.container_state_queue:
                            if container2[1] - 1 == index:
                                if (container2[0] != -1) and not (self.deployw(container1,container2)):
                                    cost = cost + container_graph[container2[1] - 1]
        return math.exp((cost * 10) / total)

    def deployw(self,a, b):
        if a[0] < 2 and b[0] < 2:
            return True
        elif 2 <= a[0] < 4 and 2 <= b[0] < 4:
            return True
        elif 4 <= a[0] < 6 and 4 <= b[0] < 6:
            return True
        else:
            return False

    def CalcuVar(self):
        NodeCPU = []
        NodeMemory = []
        Var = 0
        for i in range(len(self.node_state_queue)):
            # TODO::改成利用率的方差
            U = (self.node_state_queue[i][4] / self.node_state_queue[i][1]) * 100
            M = (self.node_state_queue[i][5] / self.node_state_queue[i][2]) * 100
            NodeCPU.append(U)
            NodeMemory.append(M)
            # Variance of node load
        Var += beta[0] * np.var(NodeCPU) + beta[1] * np.var(NodeMemory)
        Var = (Var * 10) / 2500
        return Var  # quzhiwei 0-10

    def update(self, action):
        if self.container_state_queue[action[0]][0] == -1:
            # update container state
            self.container_state_queue[action[0]][0] = action[1]
            # update node state
            self.node_state_queue[action[1]][4] = self.node_state_queue[action[1]][4] + \
                                                  self.container_state_queue[action[0]][2]
            self.node_state_queue[action[1]][5] = self.node_state_queue[action[1]][5] + \
                                                  self.container_state_queue[action[0]][3]
            self.action_queue.append(action)
            self.State = list(itertools.chain.from_iterable(self.container_state_queue + self.node_state_queue))

    def cost(self, action):
        re = 0

        g1 = self.CalcuCost2(action)
        #g1 = self.CalcuAllCost()
        # g1 = g1 / 371.5
        g2 = self.CalcuVar()
        # if g2 < 0:
        #     g2 = -100
        # alpha = 0.5
        re += alpha * g1 - (1 - alpha) * g2
        return re

    def step(self, action):
        action = [int(i) for i in action]
        self.update(action)
        cost = -self.cost(action)
        #cost = - 50 / (self.CalcuAllCost() * alpha + (1 - alpha) * self.CalcuVar() + 1)
        #cost = 5 * (1 - math.log(cost + 1) / math.log(20 + 1))
        done = False
        count = 0
        for i in range(len(self.container_state_queue)):
            if self.container_state_queue[i][0] != -1:
                count += 1
        if count == len(self.container_state_queue):
            done = True
            cost = 5000 / (self.CalcuAllCost() * alpha + (1 - alpha) * self.CalcuVar())
            if cost < 100:
                cost = -100
            # if len(self.all_reward) <= 50:
            #     self.all_reward.append(cost)
            # elif cost > max(self.all_reward):
            #     self.all_reward.append(cost)
            #     cost = cost * 3
            # elif cost > np.mean(self.all_reward):
            #     self.all_reward.append(cost)
            #     cost = cost * 2
            # elif (np.mean(self.all_reward)-cost) / np.mean(self.all_reward) > 0.2:
            #     cost = -1000 * (max(self.all_reward)-cost)/max(self.all_reward)
        else:
            #cost = 3 * count / (self.CalcuAllCost() * alpha + (1 - alpha) * self.CalcuVar() + 1)
            cost = self.cost(action)

        return self.State, cost, done

    def reset(self):
        self.prepare()
        return self.State

    def index_to_act(self, index):
        # 动作一维到二维的映射
        act = [-1, -1]
        act[0] = int(index / len(self.node_state_queue))
        act[1] = index % len(self.node_state_queue)
        return act
