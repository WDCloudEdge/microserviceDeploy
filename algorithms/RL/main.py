import sys
import numpy as np
import logging
import copy
import os

import torch

from algorithms.RL.env import Env
from algorithms.RL.agent import Agent

LEARN_FREQ = 8  # learning frequency
MEMORY_SIZE = 20000  # size of replay memory
MEMORY_WARMUP_SIZE = 200
BATCH_SIZE = 64
LEARNING_RATE = 0.0001
DEFAULT_GAMMA = 0.95


def get_gamma() -> float:
    raw = os.environ.get("DRDQL_GAMMA", "").strip()
    if raw == "":
        return float(DEFAULT_GAMMA)
    try:
        v = float(raw)
    except ValueError:
        return float(DEFAULT_GAMMA)
    if v < 0:
        return 0.0
    if v > 1:
        return 1.0
    return v

node_map = {
    "node-5": 0,
    "node-7": 1,
    "node-219": 2,
    "node-221": 3,
    # "node-218": 4,
    "node-6": 4,
    "node-227": 5,
}

service_index_map = {
    "details-v1": 1,
    "productpage-v1": 2,
    "ratings-v1": 3,
    "reviews-v1": 4,
    "reviews-v2": 5,
    "reviews-v3": 6,
}

index_service_map = {
    0: "details-v1",
    1: "productpage-v1",
    2: "ratings-v1",
    3: "reviews-v1",
    4: "reviews-v2",
    5: "reviews-v3",
}

class RL():
    def __init__(self, NodeState, ServiceGraph, ServiceResource, ServiceContainernum, graph):
        # State
        self.NodeResource = NodeState
        self.ServiceGraph = ServiceGraph
        self.ServiceResource = ServiceResource
        self.ServiceContainernum = ServiceContainernum
        self.ResultD = []
        self.ResultScore = []
        self.graph = graph


def train(nodeState, ServiceGraph, ServiceResource, ServiceContainernum, graph):
    print(torch.cuda.is_available())
    env = Env(nodeState, ServiceGraph, ServiceResource, ServiceContainernum)
    env1 = Env(nodeState, ServiceGraph, ServiceResource, ServiceContainernum)
    action_dim = len(nodeState) * len(env.container_state_queue)  # 动作空间
    obs_shape = len(env.container_state_queue) * 4 + len(env.node_state) * 6  # 状态空间的纬度
    # obs_dim = pow(len(nodeState) + 1, len(env.container_state_queue))
    gamma = get_gamma()
    logging.info("RL using gamma=%s (DRDQL_GAMMA=%s)", gamma, os.environ.get("DRDQL_GAMMA", ""))
    agent = Agent(state_shape=obs_shape, act_dim=action_dim, gamma=gamma, alpha=LEARNING_RATE, epsilon=0.1)
    max_episodes = 3000  # 最大训练轮次
    # max_step = 10000
    rewards = []  # 用于记录每轮的累计奖励
    actions_list = []
    cost = 0.0
    step = 0
    # agent.init_q_table_from_plk()
    # agent.init_ƒq_table(env)
    for episode in range(max_episodes):
        step = 0
        # 环境重置并获取初始状态
        total_reward = 0
        env.reset()
        # 动态随机探索
        epsilon_start = 0.5
        epsilon_min = 0.05
        decay = 0.0005
        temp_epsilon = max(epsilon_min, epsilon_start - decay * episode)
        while True:
            # for step in range(max_steps):
            # 智能体选择动作
            step += 1
            agent.epsilon = temp_epsilon/(len(env.action_queue) + 1)
            # print(step)
            # if step > 1000:
            #     print("a")
            #     print("b")
            done = False
            action_index = agent.sample(env.State)
            action = env.index_to_act(action_index)
            # 在环境中执行动作
            if env.if_invalid_state(agent):
                break
            else:
                while not env.if_valid_action(action):
                    action_index = agent.sample(env.State)
                    action = env.index_to_act(action_index)
            next_state, reward, done = env.step(action)
            if (not done) and (env.if_invalid_state(agent)):
                reward = 0
            # 存储经验并更新智能体
            agent.store_transition(env.State, action_index, reward, next_state, done)
            loss = agent.learn()
            with open("reward.txt", "a") as f:
                f.write("%d,%.3f \n" % (episode, reward))
            # agent.learn(state, action_index, reward, next_state, done)
            # 更新当前状态
            # 如果任务完成则退出当前轮次
            if done:
                total_reward = reward
                rewards.append(total_reward)
                actions_list.append(env.action_queue)

                #for action in env.action_queue:
                    # DE = [[4,0],[3,1],[1,2],[4,3],[2,4],[4,5],[2,6],[0,7],[5,8],[3,9]]
                    # MB = [[0, 2],  [1, 3], [2, 1], [3, 3], [4, 0] ,[5, 1], [6, 4], [7, 5], [8, 0] ,[9, 0]]
                    # RMS = [[4, 3], [7, 0], [8, 2], [3, 2], [2, 2], [0, 0], [5, 2], [9, 4], [6, 0], [1, 0]]
                    # RSDQL = [[0,4], [1,4], [5,0] ,[7,5], [9,4] ,[3,5], [4,4] ,[6,5], [8,0] ,[2,5]]
                    # RL= [[9, 3], [1, 4], [3, 5], [0, 1], [6, 3], [5, 5], [2, 1], [4, 1], [7, 0], [8, 2]]
                cost = 0
                for container1 in env.action_queue:
                    for index, item in enumerate(ServiceGraph):
                        if item != 0:
                            for container2 in env.action_queue:
                                if container2[0] == index:
                                    # 跨网段延迟
                                    # if not deployw(container1, container2):
                                    #     cost = cost + ServiceGraph[container1[0]][container2[0]]
                                    # TODO 计算总延迟需要根据graph算上权重，先固定权重0.9875
                                    # 之前在graph中已经跨网段的延迟如果部署之后没有跨网段需要乘上1-权重，仍然跨网段保留原值
                                    # 之前在graph中没有跨网段的延迟如果部署之后没有跨网段保留原值，跨网段需要除以1-权重
                                    old_container1_node_index = node_map[graph[index_service_map[container1[0]]]]
                                    old_container2_node_index = node_map[graph[index_service_map[container2[0]]]]
                                    new_container1_node_index = container1[1]
                                    new_container2_node_index = container2[1]

                                    a = 50
                                    # 如果之前的没有跨网段
                                    if deployw(old_container1_node_index, old_container2_node_index):
                                        # 如果现在的没有跨网段
                                        if deployw(new_container1_node_index, new_container2_node_index):
                                            # cost = cost + ServiceGraph[container1[0]][container2[0]]
                                            pass
                                        else:
                                            cost = cost + ServiceGraph[container1[0]][container2[0]] + a
                                    # 如果之前的有跨网段
                                    else:
                                        # 如果现在的没有跨网段
                                        if deployw(new_container1_node_index, new_container2_node_index):
                                            # cost = cost + ServiceGraph[container1[0]][container2[0]] * (1 - a)
                                            pass
                                        else:
                                            cost = cost + ServiceGraph[container1[0]][container2[0]]

                print(f"Episode {episode}, total_reward: {reward:.3f}, now: {agent.predict1(env1.State)}, cost:{cost}")
                break
            # logging.info('step:{} reward:{} Action:{}'.format(step, reward, action))
        # 记录当前轮次的总奖励

        if loss is not None:
            with open("trainloss.txt", "a") as f:
                f.write("%d,%.3f \n" % (episode, loss))
            print(
                f"Episode {episode}, Loss: {loss:.3f}")
        if episode % 600 == 0 and not episode == 0:
            agent.memory.clear()
            agent.priorities.clear()
        if episode % 100 == 0:
            agent.update_target_network()
        if episode % 10 == 0 and not episode==0:
            for i in range(1):
                step = 0
                env.reset()
                agent.epsilon = 0
                # 评估分支下每轮都重置 cost，避免沿用上次/非数值
                cost = 0.0
                while True:
                    action_index = agent.predict(env.State)
                    action = env.index_to_act(action_index)
                    # 在环境中执行动作
                    if env.if_invalid_state(agent):
                        break
                    elif not env.if_valid_action(action):
                        break
                    next_state, reward, done = env.step(action)
                if done:
                    cost = 0
                    for container1 in env.action_queue:
                        for index, item in enumerate(ServiceGraph):
                            if item != 0:
                                for container2 in env.action_queue:
                                    if container2[0] == index:
                                        if not deployw(container1, container2):
                                            cost = cost + ServiceGraph[container1[0]][container2[0]]
                with open("evl.txt", "a") as f:
                    f.write("%d,%.3f \n" % (episode, cost))
        progress = episode / max_episodes
        block = int(50 * progress)
        bar = "█" * block + "-" * (50 - block)
        percent = progress * 100
        sys.stdout.write(f"\r[{bar}] {percent:.2f}% ({episode}/{max_episodes})")
        sys.stdout.flush()
        logging.info('episode:{} totalReward:{} Actions:{}'.format(
                episode, total_reward, env.action_queue))

    logging.info('maxReward:{} maxActions:{}'.format(
        rewards[np.argmax(rewards)], actions_list[np.argmax(rewards)]))
    # last：从训练末尾向前找，最后一个 totalReward > 0 的回合（与“最后一轮”不同）
    # last_pos_reward, last_pos_actions = None, None
    # for i in range(len(rewards) - 1, -1, -1):
    #     if rewards[i] > 0:
    #         last_pos_reward = rewards[i]
    #         last_pos_actions = actions_list[i]
    #         break
    # if last_pos_reward is None:
    #     logging.warning(
    #         "lastReward/lastActions: 未出现 totalReward>0 的完成回合，last 记为 None"
    #     )
    # logging.info('lastReward:{} lastActions:{}'.format(
    #     last_pos_reward, last_pos_actions))


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
    train(NodeState, ServiceGraph, ServiceResource, ServiceContainernum, graph)
