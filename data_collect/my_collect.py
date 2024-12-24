import sys
from Config import Config
import MetricCollector
import time
import datetime
import argparse
import os


user_timestamp = str(int(time.time()))
data_folder = r'E:\research\experiment\experiment_data\baseline\random\\' + user_timestamp

def collect(begin_time, end_time):
    # namespaces = ['bookinfo', 'hipster', 'hipster2', 'sock-shop', 'horsecoder-test', 'horsecoder-minio']
    namespaces = ['test-node']
    config = Config()#2024-10-17 16:56:35
    # begin = datetime.datetime(2024, 11, 20, 14, 59, 33)
    begin = datetime.datetime.strptime(begin_time, '%Y-%m-%d %H:%M:%S')
    begin_timestamp = int(begin.timestamp())
    # end = datetime.datetime(2024, 11, 20, 15, 39, 42)
    end = datetime.datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
    end_timestamp = int(end.timestamp())
    global_now_time = begin_timestamp
    global_end_time = end_timestamp
    now = int(time.time())
    if global_now_time > now:
        sys.exit("begin time is after now time")
    if global_end_time > now:
        global_end_time = now
    for n in namespaces:
        config.namespace = n
        config.svcs.clear()
        config.pods.clear()
        count = 1
        now_time = global_now_time
        end_time = global_end_time
        
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        while now_time < end_time:
            config.start = int(round(now_time))
            config.end = int(round(now_time + config.duration))
            if config.end > end_time:
                config.end = end_time
            if count == 1:
                is_header = True
            else:
                is_header = False
            print('第' + str(count) + '次获取 [' + config.namespace + '] 数据')
            MetricCollector.collect_request_bytes(config, data_folder, is_header)
            MetricCollector.collect_request_times(config, data_folder, is_header)
            MetricCollector.collect_response_bytes(config, data_folder, is_header)
            MetricCollector.collect_svc_metric(config, data_folder, is_header)
            MetricCollector.collect_svc_latency(config, data_folder, is_header)
            MetricCollector.collect_svc_qps(config, data_folder, is_header)
            MetricCollector.collect_succeess_rate(config, data_folder, is_header)
            MetricCollector.collect_node_metric(config, data_folder, is_header)
            now_time += config.duration + 1
            config.pods.clear()
            count += 1

def main():
    parser = argparse.ArgumentParser(description="Collect start and end times")
    parser.add_argument('--start-time', type=str, help="开始时间")
    parser.add_argument('--end-time', type=str, help="结束时间")
    args = parser.parse_args()
    collect(args.start_time, args.end_time)

if __name__ == "__main__":
    main()