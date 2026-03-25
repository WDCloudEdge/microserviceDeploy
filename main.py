import importlib
import os
import time
import csv

from fastapi import FastAPI
import uvicorn
import logging
import json
# from kubernetes import client, config

logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为 INFO
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log.txt', mode='a'),  # 将日志写入到 'log.txt'
        logging.StreamHandler()  # 同时输出到控制台，避免“看起来没反应”
    ]
)

app = FastAPI()
ResultScore = None


@app.get('/api/endpoint')
async def endpoint():
    return {"ResultScore": ResultScore}


def check_modules_in_file(file_path, algorithm_name):
    # algorithm_list = []
    # with open(file_path, 'r') as file:
    #     for line in file:
    #         if line.startswith('#'):
    #             continue
    module_name = '.' + algorithm_name + '.main'
    algorithm = importlib.import_module(module_name, package='algorithms')
    return algorithm


def start_exp(algorithm, NodeStates, ServiceGraph, ServiceResource, ServiceContainernum, graph):
    logging.info('Start algorithm execution: %s', getattr(algorithm, '__name__', str(algorithm)))
    start_time = int(time.time() * 1000)
    ResultScore = algorithm.get_result(NodeStates, ServiceGraph, ServiceResource, ServiceContainernum, graph)
    end_time = int(time.time() * 1000)
    # objective = get_objective(NodeState, ServiceGraph, ServiceContainernum, ContainerRelationship,
    #                           ResultD)
    # objective.set_efficiency(end_time - start_time)
    efficiency = end_time - start_time
    logging.info('Algorithm finished in %d ms', efficiency)
    return ResultScore, efficiency


def remove_first_row_column(file_path):
    outfile = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            outfile.append([float(value) for value in row[1:]])  # 去掉第一列并转换为浮点数
    return outfile

def remove_first_row_column_graph(file_path):
    location_map = {}
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            if "node" in row[1]:
                index = find_nth(row[0], "-", 2)
                location_map[row[0][:index]] = row[1]  # 去掉第一列并转换为浮点数
    return location_map

def find_nth(s, char, n):
    pos = -1
    start = 0
    for _ in range(n):
        pos = s.find(char, start)
        if pos == -1:
            return -1
        start = pos + 1
    return pos

def remove_first_row(file_path):
    outfile = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            outfile.append([float(value) for value in row])  # 去掉第一列并转换为浮点数
    return outfile


if __name__ == '__main__':
    # 获取用户目录
    runConfig = None
    with open('config.json', 'r') as f:
        runConfig = json.load(f)
    runConfigUser = runConfig['user']
    runConfigType = runConfig['type']
    runConfigSystem = runConfig['system']
    runConfigAlgorithm = runConfig['algorithm']
    # 获取节点信息


    # dataBaseFilePath = '/home/inspur/' + runConfigUser + '/algorithms/data/'+ runConfigUser +'/'+ runConfigSystem + '/' + runConfigType + '/'
    dataBaseFilePath = 'data/' + runConfigUser + '/' + runConfigSystem + '/' + runConfigType + '/'
    ContainerNumber = 0  # 实例总数
    NodeNumber = 0  # 节点数量
    ServiceNumber = 0  # 服务数量
    ServiceContainernum = []  # 每个服务对应的实例数量
    ContainerRelationship = []
    ServiceGraph = remove_first_row_column(dataBaseFilePath + '400user_metrics/ServiceGraph.csv')
    graph = remove_first_row_column_graph(dataBaseFilePath + '400user_metrics/graph.csv')
    NodeStates = remove_first_row(dataBaseFilePath + 'node.csv')

    # if runConfigType == 'real':
    #     kubeconfig_path = "config"
    #     config.load_kube_config(config_file=kubeconfig_path)
    #     v1 = client.CoreV1Api()
    #     metrics_api = client.CustomObjectsApi()
    #     nodes = v1.list_node()
    #     10user_metrics = metrics_api.list_cluster_custom_object(group="10user_metrics.k8s.io", version="v1beta1", plural="nodes")
    #     for node in nodes.items:
    #         if node.metadata.name == "izn4ad6ep6e1d872lfbldiz" :
    #             continue
    #         capacity = node.status.allocatable
    #         for nodeStates in NodeStates:
    #             for item in 10user_metrics["items"]:
    #                 if (node.metadata.name == item["metadata"]["name"]) & (node.metadata.name == nodeStates[0]):
    #                     nodeStates[1] = float(capacity["cpu"]) * 1000 - float(item["usage"]["cpu"][:-1]) / (1000 * 1000)
    #                     nodeStates[2] = (float(capacity["memory"][:-2]) - float(item["usage"]["memory"][:-2])) / (1024)
    ServiceResource = remove_first_row_column(dataBaseFilePath + '400user_metrics/ServiceResource.csv')
    with open(dataBaseFilePath + 'replicas.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            ServiceContainernum = [int(value) for value in row]
            break

    # algorithms_file_path = '/home/inspur/' + runConfigUser + '/algorithms/algs'
    algorithms_file_path = 'algs'
    try:
        algorithm = check_modules_in_file(algorithms_file_path, runConfigAlgorithm)
    except ImportError as e:
        raise e
    for num in ServiceContainernum:
        ContainerNumber += num
    NodeNumber = len(NodeStates)
    ServiceNumber = len(ServiceContainernum)
    for i, num in enumerate(ServiceContainernum):
        for _ in range(num):
            ContainerRelationship.append(i)
    # ServiceBaseTime = [20] * 11
    # ServiceBaseTime[0] = 40
    # pydevd_pycharm.settrace('10.128.134.216', port=12345, stdoutToServer=True, stderrToServer=True)
    ResultScore, efficiency = start_exp(algorithm, NodeStates, ServiceGraph, ServiceResource,
                                        ServiceContainernum, graph)
    # logging.info('\t{}: algorithm efficiency: {}, ResultScore:{}'.format(
    #     algorithm.__name__, efficiency, ResultScore))
    if os.environ.get("DRDQL_SKIP_UVICORN", "").strip() in ("1", "true", "yes"):
        logging.info("DRDQL_SKIP_UVICORN set: skip uvicorn (batch/script mode)")
    else:
        logging.info('Starting FastAPI server at 0.0.0.0:5012')
        uvicorn.run(app, host='0.0.0.0', port=5012)
