import time
import math
from collections import defaultdict
from util.KubernetesClient import KubernetesClient
from util.PrometheusClient import PrometheusClient
from config.Config import Config
import networkx as nx
import matplotlib.pyplot as plt
import random
from matplotlib.animation import FuncAnimation
a = 0.5
b = 0.5
def count_edges_in_subset(G, subset):
    edge_count = 0
    
    # 遍历图中的每一条边
    for u, v in G.edges():
        # 检查边的起点 u 和终点 v 是否都在子集 S 中
        if u in subset and v in subset:
            edge_count += 1
    
    return edge_count

class Cluster:
    def __init__(self, config:Config, nodeStates, containerResource):
        self.prom_util = PrometheusClient(config)
        self.k8s_util = KubernetesClient(config)
        self.nodeStates = nodeStates
        self.containerResource = {item[0]: item[1:] for item in containerResource}
        # ----------怎么把资源限制考虑进去？还是暂时不考虑？---------------

    #获取微服务对之间的调用次数
    def get_calls(self):
        # get all call latency last 1min
        begin = int(round((time.time() - 60)))
        end = int(round(time.time()))
        self.prom_util.set_time_range(begin, end)
        # slo Hypothesis testing
        calls = []
        call_latency, call_times = self.prom_util.collect_request_times()
        for call in call_latency:
            calls.append(call)
        return calls, call_times
    
    #利用微服务调用关系构建调用图，get_calls的返回的第一个值为调用关系
    def build_graph(self, calls):
        dg = nx.DiGraph()
        for call in calls:
            nodes = call.split('_')
            for node in nodes:
                if node not in dg:
                    dg.add_node(node)
            for i in range(len(nodes) - 1):
                dg.add_edge(nodes[i], nodes[i + 1])
        return dg
    
    #获取每个微服务被调用次数
    def get_frequency(self):
        # get all call latency last 1min
        begin = int(round((time.time() - 60)))
        end = int(round(time.time()))
        self.prom_util.set_time_range(begin, end)
        return self.prom_util.get_svc_qps_range()
    
    #获取微服务对之间1min传输的数据量
    def get_communication_bytes(self):
        begin = int(round((time.time() - 60)))
        end = int(round(time.time()))
        self.prom_util.set_time_range(begin, end)
        return self.prom_util.collect_communication_bytes()
    def aboutDep(self, depData, microservice1, microservice2):
        call = microservice1 + '_' + microservice2
        call_exchange = microservice2 + '_' + microservice1
        dD1 = depData[call]
        dD2 = depData[call_exchange]
        if dD1 is None and dD2 is None:
            return 0
        return dD1 if dD1 is not None else dD2
    def clustering(self, n):
        calls, NumSvs = self.get_calls()
        G = self.build_graph(calls)
        in_degree_centrality = nx.in_degree_centrality(G)
        out_degree_centrality = nx.out_degree_centrality(G)
        total_degree_centrality = {node: in_degree_centrality[node] + out_degree_centrality[node]
                                for node in G.nodes()}
        DepIC = {}
        NumSv = self.get_frequency()
        DepData = self.get_communication_bytes()
        Dep = {}
        for call in calls:
            DepIC[call] = 0
            nodes = call.split('_')
            for node in nodes:
                DepIC[call] += (1 / (total_degree_centrality[node] + NumSv[node]))
            DepIC[call] *= NumSvs[call]
            Dep[call] = a * DepIC[call] + b * DepData[call]
        microservices = G.nodes()
        clusters = [set([microservice]) for microservice in microservices]
        while len(clusters) > n:
            best_cluster1 = None
            best_cluster2 = None
            max_compactness = 0
            for cluster1 in clusters:
                for cluster2 in clusters:
                    if cluster1 != cluster2:
                        min_distance = min(
                            self.aboutDep(DepData, microservice1, microservice2)
                            for microservice1 in cluster1
                            for microservice2 in cluster2
                        )
                    if min_distance > 0:
                        candidate_cluster = cluster1.union(cluster2)
                        # 计算候选集群的紧密度
                        compactness = sum(
                            self.aboutDep(Dep, microservice1, microservice2)
                            for microservice1 in candidate_cluster
                            for microservice2 in candidate_cluster
                        ) / count_edges_in_subset(G, candidate_cluster)
                    if compactness > max_compactness:
                        best_cluster1 = cluster1
                        best_cluster2 = cluster2
                        max_compactness = compactness
            # 合并两个最佳集群
            clusters.remove(best_cluster1)
            clusters.remove(best_cluster2)
            clusters.append(best_cluster1.union(best_cluster2))
        return clusters