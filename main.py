import importlib
import time
import csv
from algorithms.objective import get_objective
from fastapi import FastAPI
import uvicorn
import logging

logging.basicConfig(
    level=logging.INFO,  # 设置日志级别为 INFO
    format='%(asctime)s - %(levelname)s - %(message)s',  # 日志的格式
    handlers=[
        logging.StreamHandler()  # 输出到控制台
    ]
)

app = FastAPI()
ResultScore=None
@app.get('/api/endpoint')
async def endpoint():
    return {"ResultScore": ResultScore}

def check_modules_in_file(file_path):
    algorithm_list = []
    with open(file_path, 'r') as file:
        for line in file:
            if line.startswith('#'):
                continue
            module_name = '.' + line.strip() + '.main'
            algorithm = importlib.import_module(module_name, package='algorithms')
            algorithm_list.append(algorithm)
    return algorithm_list


def start_exp(algorithm, NodeState, ServiceGraph, ServiceBaseTime, ServiceResource, ServiceContainernum, ContainerRelationship):
    start_time = int(time.time() * 1000)
    ResultD, ResultScore, NodeState = algorithm.get_result(NodeState, ServiceGraph, ServiceBaseTime, ServiceResource, ServiceContainernum, ContainerRelationship)
    end_time = int(time.time() * 1000)
    objective = get_objective(NodeState, ServiceGraph, ServiceBaseTime, ServiceContainernum, ContainerRelationship, ResultD)
    objective.set_efficiency(end_time - start_time)
    return ResultScore, objective

def remove_first_row_column(file_path):
    outfile = []
    with open(file_path, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # 跳过表头
        for row in reader:
            outfile.append([float(value) for value in row[1:]])  # 去掉第一列并转换为浮点数
    return outfile

if __name__ == '__main__':
    #运行算法
    algorithms_file_path = '/home/inspur/txx/wcx/algorithms/algs'
    try:
        algorithm_list = check_modules_in_file(algorithms_file_path)
        # print('load algorithms:')
        # for algorithm in algorithm_list:
        #     print('\t' + algorithm.__name__)
    except ImportError as e:
        raise e

    for algorithm in algorithm_list:
        ContainerNumber = 0
        NodeNumber = 0
        ServiceNumber = 0
        NodeState = []
        ServiceContainernum = []
        ServiceGraph = []
        ServiceResource = []
        ContainerRelationship = []
        # 读取 CSV 文件
        ServiceGraph = remove_first_row_column('/home/inspur/txx/wcx/algorithms/data/ServiceGraph.csv')
        NodeState = remove_first_row_column('/home/inspur/txx/wcx/algorithms/data/node.csv')
        ServiceResource = remove_first_row_column('/home/inspur/txx/wcx/algorithms/data/ServiceResource.csv')
        with open('/home/inspur/txx/wcx/algorithms/data/replicas.csv', 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                ServiceContainernum = [int(value) for value in row]
                break
        for num in ServiceContainernum:
            ContainerNumber += num
        NodeNumber = len(NodeState)
        ServiceNumber = len(ServiceContainernum)
        for i, num in enumerate(ServiceContainernum):
            for _ in range(num):
                ContainerRelationship.append(i)
        ServiceBaseTime = [20] * 11
        ServiceBaseTime[0] = 40
        ResultScore, objective = start_exp(algorithm, NodeState, ServiceGraph, ServiceBaseTime, ServiceResource, ServiceContainernum, ContainerRelationship)
        logging.info('\t{}: latency: {}, algorithm efficiency: {}, ResultScore:{}'.format(
            algorithm.__name__, objective.Latency, objective.Efficiency, ResultScore))


        uvicorn.run(app, host='0.0.0.0', port=5011)


