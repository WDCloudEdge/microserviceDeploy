import numpy as np
import sys
import random
import pickle
import torch
import torch.nn as nn
import torch.optim as optim
from collections import deque
import time
import logging
#device = torch.device("cpu")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
from algorithms.RL.model import QNetwork


class Agent:
    def __init__(self, state_shape, act_dim, gamma, alpha, epsilon):
        self.state_shape = state_shape  # 状态空间维度
        self.act_dim = act_dim  # 动作空间维度
        self.gamma = gamma  # 折扣因子
        self.alpha = alpha  # 学习率
        self.epsilon = epsilon  # 探索率
        #self.q_table = np.zeros((state_dim, act_dim), dtype=np.float64)  # 初始化 Q 表
        self.q_network = QNetwork(state_shape, act_dim).to(device)
        self.target_network = QNetwork(state_shape, act_dim).to(device)  # 目标网络
        self.optimizer = optim.Adam(self.q_network.parameters(), lr=alpha)  # 使用 Adam 优化器
        self.memory = deque(maxlen=5000)
        self.priorities = deque(maxlen=5000)# 经验回放缓冲区
        self.batch_size = 64
        self.update_target_network()

    # def init_q_table_from_plk(self):
    #     with open("RL_init_q_table.pkl", "rb") as file:
    #         self.q_table = pickle.load(file)
    #         self.q_table = self.q_table.astype(np.float64)
    #
    #
    # def save_q_table(self):
    #     """保存 q_table 到文件"""
    #     with open("RL_init_q_table.pkl", 'wb') as f:
    #         pickle.dump(self.q_table, f)
    #
    #
    # def init_q_table(self, env):
    #     count = 0
    #     for i in range(self.q_table.shape[0]):
    #         progress = i / self.q_table.shape[0]
    #         block = int(50 * progress)
    #         bar = "█" * block + "-" * (50 - block)
    #         percent = progress * 100
    #         sys.stdout.write(f"\r[{bar}] {percent:.2f}% ({i}/{self.q_table.shape[0]})")
    #         sys.stdout.flush()
    #         temp_count = 0
    #         state = self.index_to_state(i)
    #         for j in range(self.q_table.shape[1]):
    #             node_used_cpu = 0
    #             node_used_mem = 0  # 遍历列
    #             action = self.index_to_act(j)
    #             #状态异常
    #             #动作异常
    #             if state[action[0]] != -1:
    #                 self.q_table[i][j] = -1000
    #                 temp_count = temp_count + 1
    #             else:
    #                 for index, k in enumerate(state):
    #                     if k == -1:
    #                         continue
    #                     if k == action[1]:
    #                         node_used_cpu = node_used_cpu + env.container_state_queue[index][2]
    #                         node_used_mem = node_used_mem + env.container_state_queue[index][3]
    #                 if (env.node_state_queue[action[1]][1] < node_used_cpu + env.container_state_queue[action[0]][
    #                     2]) | (
    #                         env.node_state_queue[action[1]][2] < node_used_mem + env.container_state_queue[action[0]][
    #                     3]):
    #                     self.q_table[i][j] = -1000
    #     self.save_q_table()
    #     return count

    def update_target_network(self):
        """同步目标网络"""
        self.target_network.load_state_dict(self.q_network.state_dict())

    def predict(self, state):
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(device)  # 转换为张量
        q_values = self.q_network(state_tensor)
        return torch.argmax(q_values).item()
        #return np.argmax(self.q_table[state])
        # 返回 Q 值最大的动作
    def predict1(self, state):
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(device)  # 转换为张量
        q_values = self.q_network(state_tensor)
        return q_values

    def sample(self, state):
        if random.random() < self.epsilon:
            return random.randint(0, self.act_dim - 1)  # 随机探索
        else:
            return self.predict(state)  # 贪婪选择

    def store_transition(self, state, action, reward, next_state, done):
        """将转移保存到经验回放缓冲区"""
        priority = abs(reward)
        self.memory.append((state, action, reward, next_state, done))
        #print(len(self.memory))
        self.priorities.append(priority)
        #print(len(self.priorities))

    # def learn(self, state, action, reward, next_state, done):
    #     q_predict = self.q_table[self.state_to_index(state), action]
    #     q_target = reward + (0 if done else self.gamma * np.max(self.q_table[self.state_to_index(next_state)]))
    #     self.q_table[self.state_to_index(state), action] += self.alpha * (q_target - q_predict)


    def learn(self):
        """通过经验回放学习"""
        if len(self.memory) < self.batch_size:
            return

        probabilities = np.array(self.priorities)  # 根据优先级调整
        probabilities /= probabilities.sum()  # 归一化，确保概率和为1

        # 从经验回放中随机采样
        if random.random() < 1:
            batch = random.sample(self.memory,self.batch_size)
        else:
            batch = random.choices(self.memory, k=self.batch_size, weights=probabilities)

        state_batch, action_batch, reward_batch, next_state_batch, done_batch = zip(*batch)

        state_batch = torch.FloatTensor(state_batch).to(device)
        next_state_batch = torch.FloatTensor(next_state_batch).to(device)
        action_batch = torch.LongTensor(action_batch).to(device)

        reward_batch = torch.FloatTensor(reward_batch).to(device)
        #print(reward_batch)
        done_batch = torch.FloatTensor(done_batch).to(device)

        # 计算 Q 值预测
        q_values = self.q_network(state_batch)
        q_value_pred = q_values.gather(1, action_batch.unsqueeze(1)).squeeze(1)

        # 计算 Q 值目标
        q_values_next = self.q_network(next_state_batch)
        #q_values_next = self.target_network(next_state_batch)
        q_value_target = reward_batch + (1 - done_batch) * self.gamma * q_values_next.max(1)[0]

        # 计算损失函数
        loss = nn.MSELoss()(q_value_pred, q_value_target)

        # 更新 Q 网络
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        return loss

    def save_model(self):
        """保存模型"""
        torch.save(self.q_network.state_dict(), "q_network.pth")

    # def load_model(self):
    #     """加载模型"""
    #     self.q_network.load_state_dict(torch.load("q_network.pth"))
    #     self.update_target_network()

    # def state_to_index(self, state, dims=5):
    #     index = 0
    #     multiplier = 1
    #     for value in reversed(state):  # 从最后一维开始计算
    #         index += (value[0] + 1) * multiplier
    #         multiplier *= dims
    #     return index
    #
    # def state_to_index2(self, state, dims=5):
    #     index = 0
    #     multiplier = 1
    #     for value in reversed(state):  # 从最后一维开始计算
    #         index += (value + 1) * multiplier
    #         multiplier *= dims
    #     return index

    # def index_to_state(self, index):
    #     state = []
    #     for i in range(10):
    #         state.append(index % 5 - 1)
    #         index //= 5
    #     return list(reversed(state))

    def index_to_act(self, index):
        # 动作一维到二维的映射
        act = [-1, -1]
        act[0] = int(index / 4)
        act[1] = index % 4
        return act
