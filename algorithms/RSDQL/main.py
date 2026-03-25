import os
import sys
import random
from datetime import datetime

import numpy as np
import tensorflow as tf
import tensorlayer as tl


# 复用 RMS_DDPG 目录下的环境与超参数定义
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
RMS_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "RMS_DDPG")
if RMS_DIR not in sys.path:
    sys.path.insert(0, RMS_DIR)

from RMS_DDPG import MEMORY_CAPACITY, BATCH_SIZE, LR_A, TAU, GAMMA, VAR, RANDOMSEED, MAX_EPISODES  # noqa: E402
import EDGE_ENV  # noqa: E402
import EDGE_DEFINE  # noqa: E402


def _normalize_service_containers(service_container_num, target_len):
    # RSDQL 同样依赖 ms_image 做时延计算，不能出现 0
    if service_container_num is None:
        return [1] * target_len
    service_container_num = list(service_container_num)
    if len(service_container_num) >= target_len:
        raw = service_container_num[:target_len]
    else:
        raw = service_container_num + [1] * (target_len - len(service_container_num))
    normalized = []
    for x in raw:
        v = int(x)
        if v <= 0:
            v = 1
        normalized.append(v)
    return normalized


def _ensure_log_newline(log_path):
    try:
        with open(log_path, "rb") as fb:
            fb.seek(-1, os.SEEK_END)
            last = fb.read(1)
        if last not in (b"\n", b""):
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n")
    except OSError:
        pass


class DQN(object):
    def __init__(self, s_dim, a_dim):
        self.memory = np.zeros((MEMORY_CAPACITY, s_dim * 2 + a_dim + 1), dtype=np.float32)
        self.pointer = 0
        self.s_dim = s_dim
        self.a_dim = a_dim
        W_init = tf.random_normal_initializer(mean=0, stddev=0.1)
        b_init = tf.constant_initializer(0.1)
        self.qloss = []

        def qnet(in_shape):
            inputs = tl.layers.Input(in_shape, name="q_input")
            fc1 = tl.layers.Dense(n_units=128, act=tf.nn.relu, W_init=W_init, b_init=b_init, name="fc1")(inputs)
            fc2 = tl.layers.Dense(n_units=128, act=tf.nn.relu, W_init=W_init, b_init=b_init, name="fc2")(fc1)
            out = tl.layers.Dense(n_units=a_dim, act=tf.tanh, name="out")(fc2)
            return tl.models.Model(inputs=inputs, outputs=out)

        self.qnet = qnet([None, s_dim])
        self.qnet.train()

        def copy_para(from_model, to_model):
            for i, j in zip(from_model.trainable_weights, to_model.trainable_weights):
                j.assign(i)

        self.q_target = qnet([None, s_dim])
        copy_para(self.qnet, self.q_target)
        self.q_target.eval()

        self.qnet_opt = tf.optimizers.Adam(LR_A)
        self.ema = tf.train.ExponentialMovingAverage(decay=1 - TAU)

    def ema_update(self):
        paras = self.qnet.trainable_weights
        self.ema.apply(paras)
        for i, j in zip(self.q_target.trainable_weights, paras):
            i.assign(self.ema.average(j))

    def choose_action(self, s):
        return self.qnet(np.array(s, dtype=np.float32))

    def learn(self):
        indices = np.random.choice(MEMORY_CAPACITY, size=BATCH_SIZE)
        bt = self.memory[indices, :]
        bs = bt[:, :self.s_dim]
        ba = bt[:, self.s_dim:self.s_dim + self.a_dim]
        br = bt[:, -self.s_dim - 1:-self.s_dim]
        bs_ = bt[:, -self.s_dim:]

        with tf.GradientTape() as tape:
            q = self.qnet(bs)
            q_v = self.q_target(bs_)
            y = -br + GAMMA * q_v
            q_loss = tf.reduce_mean(tf.square(q - y))
        c_grads = tape.gradient(q_loss, self.qnet.trainable_weights)
        self.qnet_opt.apply_gradients(zip(c_grads, self.qnet.trainable_weights))
        self.ema_update()
        self.qloss.append(q_loss)

    def store_transition(self, s, a, r, s_):
        s = s.astype(np.float32)
        s_ = s_.astype(np.float32)
        transition = np.hstack((s, a, [[r]], s_))
        index = self.pointer % MEMORY_CAPACITY
        self.memory[index, :] = transition
        self.pointer += 1


def get_result(NodeStates, ServiceGraph, ServiceResource, ServiceContainernum, graph):
    """
    训练模式：跑完整 MAX_EPISODES，返回“最优奖励轮”的 actionlist。
    actionlist 格式：[[service_idx, node_idx], ...]
    """
    tf.random.set_seed(RANDOMSEED)
    np.random.seed(RANDOMSEED)
    random.seed(RANDOMSEED)

    node_count = len(NodeStates)
    service_count = len(ServiceResource)
    if node_count <= 0 or service_count <= 0:
        return []

    node_cpu = [float(NodeStates[i][1]) for i in range(node_count)]
    node_mem = [float(NodeStates[i][2]) for i in range(node_count)]
    ms_cpu = [float(ServiceResource[i][0]) for i in range(service_count)]
    ms_mem = [float(ServiceResource[i][1]) for i in range(service_count)]
    ms_image = _normalize_service_containers(ServiceContainernum, service_count)

    # 注入 CSV 数据到 RMS/EDGE 环境
    EDGE_DEFINE.MS_NUM = service_count
    EDGE_DEFINE.NODE_NUM = node_count
    EDGE_DEFINE.ms_image = ms_image

    def _ms_init(self, ms_id):
        self.id = ms_id
        self.cpu = ms_cpu[ms_id]
        self.memory = ms_mem[ms_id]

    def _edge_node_init(self, node_id):
        self.id = node_id
        self.xloc = float(node_id)
        self.yloc = float(node_id)
        self.cpu = node_cpu[node_id]
        self.memory = node_mem[node_id]

    EDGE_DEFINE.MS.__init__ = _ms_init
    EDGE_DEFINE.EDGE_NODE.__init__ = _edge_node_init

    EDGE_ENV.MS_NUM = service_count
    EDGE_ENV.NODE_NUM = node_count
    EDGE_ENV.ms_image = ms_image
    EDGE_ENV.edge_node = EDGE_ENV.edge_initial(EDGE_ENV.NODE_NUM)
    EDGE_ENV.user_request = EDGE_ENV.get_user_request(EDGE_ENV.USER_NUM)

    s_dim = (EDGE_ENV.MS_NUM + 2 * EDGE_ENV.RESOURCE_NUM) * EDGE_ENV.NODE_NUM
    a_dim = EDGE_ENV.NODE_NUM
    dql = DQN(s_dim, a_dim)
    t = float("inf")
    t_min = float("inf")
    reward_buffer = []
    num = sum(ms_image)
    depflag = 0

    best_reward = float("-inf")
    best_actionlist = []
    last_actionlist = []
    episode_logs = []

    for episode in range(MAX_EPISODES):
        step_rew = 0
        s = EDGE_ENV.initial_state()
        ms_list = [i for i in range(EDGE_ENV.MS_NUM)]
        ms_init_image = list(ms_image)
        flag = True
        count = 0
        actionlist = []

        while len(ms_list) != 0:
            ms_idx = random.choice(ms_list)
            ms_list.remove(ms_idx)
            image_num = ms_init_image[ms_idx]
            for _ in range(image_num):
                count += 1
                a = dql.choose_action(s)
                a = np.clip(np.random.normal(a, VAR), -1, 1)
                snew, act_idx = EDGE_ENV.update_state(s, a, ms_idx)
                actionlist.append([int(ms_idx), int(act_idx)])
                s_new = np.reshape(snew, (EDGE_ENV.MS_NUM + 2 * EDGE_ENV.RESOURCE_NUM, EDGE_ENV.NODE_NUM))

                if flag is False:
                    break
                elif s_new[EDGE_ENV.MS_NUM + 1][act_idx] > 0 and s_new[EDGE_ENV.MS_NUM + 3][act_idx] > 0 and count <= num - 1:
                    reward = count / num
                    step_rew += reward
                elif (s_new[EDGE_ENV.MS_NUM + 1][act_idx] <= 0 or s_new[EDGE_ENV.MS_NUM + 3][act_idx] <= 0) and count <= num - 1:
                    reward = 0
                    step_rew += reward
                    flag = False

                dql.store_transition(s, a, reward, snew)
                if dql.pointer > MEMORY_CAPACITY:
                    dql.learn()
                s = np.reshape(s_new, (1, s_dim))

        if flag is False:
            dql.store_transition(s, a, step_rew / 10, snew)
        elif flag is True:
            depflag += 1
            if depflag == 1:
                t_new = EDGE_ENV.cal_access_delay(s_new)
                t = t_new
                t_min = t_new
            t_new = EDGE_ENV.cal_access_delay(s_new)
            if episode > 0 and t_new <= t_min:
                reward = (t_min - t_new) * 0.5 + 1
                t_min = t_new
            elif episode > 0 and t_new < t:
                reward = (t - t_new) * 0.1 + 1
            else:
                reward = 0
            step_rew += reward
            dql.store_transition(s, a, step_rew / 10, snew)
            t = t_new

        if episode == 0:
            reward_buffer.append(step_rew * 0.05)
        else:
            reward_buffer.append(reward_buffer[-1] * 0.95 + step_rew * 0.05)

        last_actionlist = actionlist
        if step_rew > best_reward:
            best_reward = step_rew
            best_actionlist = list(actionlist)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        episode_logs.append(f"{ts} - INFO - episode:{episode} reward:{step_rew} Actions:{actionlist}\n")

    # 记录每一轮 + 最后一轮与最优轮，便于你排查
    log_path = os.path.join(CURRENT_DIR, "log.txt")
    _ensure_log_newline(log_path)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    with open(log_path, "a", encoding="utf-8") as f:
        f.writelines(episode_logs)
        f.write(f"{ts} - INFO - episode:rsdql_last reward:{reward_buffer[-1] if reward_buffer else 0} Actions:{last_actionlist}\n")
        f.write(f"{ts} - INFO - episode:rsdql_best reward:{best_reward} Actions:{best_actionlist}\n")

    # 按你的要求：返回最优奖励轮 actionlist
    return best_actionlist

