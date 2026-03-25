import os
import sys
import random
from datetime import datetime
import logging

import numpy as np


def _normalize_service_containers(service_container_num, target_len):
    """
    将 replicas.csv 读出来的实例数列表对齐到 ServiceResource 的服务数量。
    """
    # 对 RMS 环境来说，ms_image 参与除法计算，不能为 0
    # 规则：
    # - 缺失项补 1
    # - 非法/非正值统一钳制到 1
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
    """
    如果日志文件末尾没有换行符，补上，避免追加写入拼接到上一行后面。
    """
    try:
        with open(log_path, "rb") as fb:
            fb.seek(-1, os.SEEK_END)
            last = fb.read(1)
        if last not in (b"\n", b""):
            with open(log_path, "a", encoding="utf-8") as f:
                f.write("\n")
    except OSError:
        # 文件不存在或为空都直接忽略
        pass


def get_result(NodeStates, ServiceGraph, ServiceResource, ServiceContainernum):
    """
    使用 RMS_DDPG 的环境与 ddpg.choose_action + EDGE_ENV.update_state 逻辑生成 actionlist。
    cost 不作为约束；重点是“动作生成逻辑”来自 RMS_DDPG。

    输出格式：[[service_idx, node_idx], ...]（与 Random/RL 一致的扁平动作列表）
    """
    logging.info("RMS_DDPG get_result started")
    base_dir = os.path.dirname(__file__)
    logging.info("RMS_DDPG step: prepare import path")
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    # 导入 RMS 环境/模型（注意：RMS 内部使用了非相对导入，因此需要 sys.path 注入 base_dir）
    logging.info("RMS_DDPG step: importing EDGE_DEFINE/EDGE_ENV/RMS_DDPG")
    import EDGE_DEFINE
    import EDGE_ENV
    import RMS_DDPG as rms_mod
    from RMS_DDPG import RMS_DDPG
    logging.info("RMS_DDPG step: imports done")

    node_count = len(NodeStates)
    service_count = len(ServiceResource)
    if node_count <= 0 or service_count <= 0:
        return []
    np.random.seed(rms_mod.RANDOMSEED)
    random.seed(rms_mod.RANDOMSEED)

    # DRDQL 的 NodeStates: [node_id, cpu, mem, ip]
    node_cpu = [float(NodeStates[i][1]) for i in range(node_count)]
    node_mem = [float(NodeStates[i][2]) for i in range(node_count)]

    # DRDQL 的 ServiceResource: [cpu(m), mem(Mi)]
    ms_cpu = [float(ServiceResource[i][0]) for i in range(service_count)]
    ms_mem = [float(ServiceResource[i][1]) for i in range(service_count)]

    ms_image = _normalize_service_containers(ServiceContainernum, service_count)
    logging.info("RMS_DDPG step: data normalized, nodes=%d, services=%d, replicas=%d", node_count, service_count, sum(ms_image))

    # 1) 覆盖 EDGE_DEFINE 的规模与资源
    EDGE_DEFINE.MS_NUM = service_count
    EDGE_DEFINE.NODE_NUM = node_count
    EDGE_DEFINE.ms_image = ms_image

    def _ms_init(self, ms_id):
        self.id = ms_id
        self.cpu = ms_cpu[ms_id]
        self.memory = ms_mem[ms_id]

    def _edge_node_init(self, node_id):
        self.id = node_id
        # DRDQL 的 node.csv 没有 xloc/yloc；这里用 node_id 填充即可（cost 不敏感）
        self.xloc = float(node_id)
        self.yloc = float(node_id)
        self.cpu = node_cpu[node_id]
        self.memory = node_mem[node_id]

    EDGE_DEFINE.MS.__init__ = _ms_init
    EDGE_DEFINE.EDGE_NODE.__init__ = _edge_node_init

    # 2) 覆盖 EDGE_ENV 的同名全局变量（因为 EDGE_ENV 使用了 from EDGE_DEFINE import * 的拷贝）
    EDGE_ENV.MS_NUM = service_count
    EDGE_ENV.NODE_NUM = node_count
    EDGE_ENV.ms_image = ms_image

    # 重新初始化用到全局变量的缓存
    EDGE_ENV.edge_node = EDGE_ENV.edge_initial(EDGE_ENV.NODE_NUM)
    EDGE_ENV.user_request = EDGE_ENV.get_user_request(EDGE_ENV.USER_NUM)
    logging.info("RMS_DDPG step: EDGE env patched")

    # 3) RMS_DDPG 训练模式：跑完整 MAX_EPISODES，并记录每一轮 actionlist
    resource_num = EDGE_ENV.RESOURCE_NUM
    s_dim = (EDGE_ENV.MS_NUM + 2 * resource_num) * EDGE_ENV.NODE_NUM
    a_dim = EDGE_ENV.NODE_NUM
    logging.info("RMS_DDPG step: building model, s_dim=%d, a_dim=%d", s_dim, a_dim)
    ddpg = RMS_DDPG(s_dim, a_dim)
    logging.info("RMS_DDPG step: model ready")
    # 若 ms_image 全是 0，直接返回空
    if sum(ms_image) <= 0:
        return []

    t = float("inf")
    t_min = float("inf")
    depflag = 0
    num = sum(ms_image)
    reward_buffer = []
    best_reward = float("-inf")
    best_actionlist = []
    last_actionlist = []
    episode_logs = []

    logging.info("RMS_DDPG step: start training rollout, episodes=%d", rms_mod.MAX_EPISODES)
    for episode in range(rms_mod.MAX_EPISODES):
        step_rew = 0
        s = EDGE_ENV.initial_state()
        ms_list = [i for i in range(EDGE_ENV.MS_NUM)]
        ms_init_image = list(EDGE_ENV.ms_image)
        flag = True
        count = 0
        actionlist = []

        while len(ms_list) != 0:
            ms_idx = random.choice(ms_list)
            ms_list.remove(ms_idx)
            image_num = int(ms_init_image[ms_idx])
            for _ in range(image_num):
                count += 1
                s_ = np.expand_dims(s, axis=1)  # RMS 原逻辑：state (1, s_dim) -> (1,1,s_dim)
                a = ddpg.choose_action(s_)
                a = np.array(a, dtype=float)
                a = np.clip(np.random.normal(a, rms_mod.VAR), -1, 1)
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

                ddpg.store_transition(s, a, reward, snew)
                if ddpg.pointer > rms_mod.MEMORY_CAPACITY:
                    ddpg.learn()
                s = np.reshape(s_new, (1, s_dim))

        if flag is False:
            ddpg.store_transition(s, a, step_rew / 10, snew)
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
            ddpg.store_transition(s, a, step_rew / 10, snew)
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

    logging.info("RMS_DDPG step: training rollout done")

    # 4) 写日志（每一轮 + 最后一轮 + 最优轮）
    log_path = os.path.join(base_dir, "log.txt")
    _ensure_log_newline(log_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    with open(log_path, "a", encoding="utf-8") as f:
        f.writelines(episode_logs)
        f.write(f"{timestamp} - INFO - episode:rmsddpg_last reward:{reward_buffer[-1] if reward_buffer else 0} Actions:{last_actionlist}\n")
        f.write(f"{timestamp} - INFO - episode:rmsddpg_best reward:{best_reward} Actions:{best_actionlist}\n")

    logging.info("RMS_DDPG get_result finished, best_actions=%d", len(best_actionlist))
    return best_actionlist

