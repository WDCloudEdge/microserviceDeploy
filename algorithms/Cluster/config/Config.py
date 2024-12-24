import time

class Config:
    def __init__(self):
        self.namespace = 'test-node'
        self.nodes = None
        self.svcs = set()
        self.pods = set()

        self.interval = 2 * 60  # 每次收集数据的时间（10min）
        # self.interval = 60  
        # duration related to interval
        self.duration = self.interval
        self.start = int(round((time.time() - self.duration)))
        self.end = int(round(time.time()))

        # prometheus
        self.prom_range_url = "http://192.168.31.182:31213/api/v1/query_range"  # istio支持
        self.prom_range_url_node = "http://192.168.31.182:30200/api/v1/query_range"  # 原生Prometheus
        self.prom_no_range_url_node = "http://8.148.7.50:31222/api/v1/query"
        self.prom_no_range_url = "http://8.148.7.50:31213/api/v1/query"
        self.step = 5

        # jaeger
        self.jaeger_url = 'http://192.168.31.85:16686/api/traces?'
        self.lookBack = str(int(self.duration / 60)) + 'm'
        self.limit = 100000

        # kiali
        self.kiali_url = 'http://47.99.200.176:32001/kiali/api'

        # kubernetes
        self.k8s_config = 'config.yaml'  # kubernetes配置文件地址

        # concurrency set
        self.user = 'wcx'


class Node:
    def __init__(self, name, ip, node_name, cni_ip, status):
        self.name = name
        self.ip = ip
        self.node_name = node_name
        self.cni_ip = cni_ip
        self.status = status


class Pod:
    def __init__(self, node, namespace, host_ip, ip, name):
        self.node = node
        self.namespace = namespace
        self.host_ip = host_ip
        self.ip = ip
        self.name = name
