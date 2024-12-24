#!/bin/bash

# 设置初始参数
start=200
end=200
increment=20
start_time=$(date "+%Y-%m-%d %H:%M:%S")
echo "Start Time: $start_time" > test_time.log
for (( i=start; i<=end; i+=increment )); do
    # 启动 Locust 命令并获取进程ID
    locust -f  ./locustfile.py  --headless -u $i -r 10 -t 300s --csv ./test/locust$i.vcs  # 替换为实际的 Locust 指令
   # 获取占用 8089 端口的进程 PID
    PID=$(lsof -i:8089)
    echo $PID
    kill -9 $PID
    # 输出信息
    echo "已执行并终止 Locust 指令: locust -c $i -f my_locust_file.py --host http://example.com"
done
end_time=$(date "+%Y-%m-%d %H:%M:%S")
echo "End Time: $end_time" >> test_time.log
python -u "e:\research\my_deployment\data_collect\my_collect.py" --start-time "$start_time" --end-time "$end_time"