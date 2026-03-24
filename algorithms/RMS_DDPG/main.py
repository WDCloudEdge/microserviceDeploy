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
    if service_container_num is None:
        return [0] * target_len
    service_container_num = list(service_container_num)
    if len(service_container_num) >= target_len:
        return [int(x) for x in service_container_num[:target_len]]
    return [int(x) for x in service_container_num] + [0] * (target_len - len(service_container_num))


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

    # 3) RMS_DDPG 推理式生成 actionlist
    resource_num = EDGE_ENV.RESOURCE_NUM
    s_dim = (EDGE_ENV.MS_NUM + 2 * resource_num) * EDGE_ENV.NODE_NUM
    a_dim = EDGE_ENV.NODE_NUM
    logging.info("RMS_DDPG step: building model, s_dim=%d, a_dim=%d", s_dim, a_dim)
    ddpg = RMS_DDPG(s_dim, a_dim)
    logging.info("RMS_DDPG step: model ready")

    # 只跑一个 episode（足够产出 actionlist；学习/收敛不是你的重点）
    s = EDGE_ENV.initial_state()
    ms_list = list(range(EDGE_ENV.MS_NUM))
    actionlist = []

    # 若 ms_image 全是 0，直接返回空
    if sum(ms_image) <= 0:
        return []

    ms_init_image = EDGE_ENV.ms_image
    logging.info("RMS_DDPG step: start action rollout")
    while len(ms_list) != 0:
        ms_idx = random.choice(ms_list)
        ms_list.remove(ms_idx)
        image_num = int(ms_init_image[ms_idx])
        if image_num <= 0:
            continue

        for _ in range(image_num):
            # 选择动作（节点编号）
            s_ = np.expand_dims(s, axis=1)  # RMS 原逻辑：state (1, s_dim) -> (1,1,s_dim)
            a = ddpg.choose_action(s_)
            a = np.array(a, dtype=float)
            a = np.clip(np.random.normal(a, rms_mod.VAR), -1, 1)

            s, act_idx = EDGE_ENV.update_state(s, a, ms_idx)
            actionlist.append([ms_idx, int(act_idx)])
    logging.info("RMS_DDPG step: rollout done")

    # 4) 写日志（便于你对照 Actions 正则解析）
    log_path = os.path.join(base_dir, "log.txt")
    _ensure_log_newline(log_path)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
    line = f"{timestamp} - INFO - episode:rmsddpg Actions:{actionlist}\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)

    logging.info("RMS_DDPG get_result finished, actions=%d", len(actionlist))
    return actionlist

