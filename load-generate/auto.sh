#!/bin/bash

save_path='E:/research/experiment/experiment_data/baseline/random'
# save_path='E:/research/experiment/experiment_data/baseline/RSDQL'
# save_path='E:/research/experiment/experiment_data/baseline/cluster'
mkdir -p "$save_path"
start=20
end=80
increment=20
start2=100
end2=800
increment2=100
start_time=$(date "+%Y-%m-%d %H:%M:%S")
echo "Start Time: $start_time" > "$save_path/test_time${start_time}.log"
for (( i=start; i<=end; i+=increment )); do
    # 启动 Locust 命令并获取进程ID
    locust -f  ./locustfile.py  --headless -u $i -r 10 -t 60s --csv $save_path/locust${i}${start_time}.vcs  # 替换为实际的 Locust 指令
   # 获取占用 8089 端口的进程 PID
    PID=$(lsof -i:8089)
    echo $PID
    kill -9 $PID
    # 输出信息
    echo "已执行并终止 Locust 指令: locust -c $i -f my_locust_file.py --host http://example.com"
done
for (( i=start2; i<=end2; i+=increment2 )); do
    # 启动 Locust 命令并获取进程ID
    locust -f  ./locustfile.py  --headless -u $i -r 50 -t 120s --csv $save_path/locust${i}${start_time}.vcs  # 替换为实际的 Locust 指令
   # 获取占用 8089 端口的进程 PID
    PID=$(lsof -i:8089)
    echo $PID
    kill -9 $PID
    # 输出信息
    echo "已执行并终止 Locust 指令: locust -c $i -f my_locust_file.py --host http://example.com"
done
end_time=$(date "+%Y-%m-%d %H:%M:%S")
echo "End Time: $end_time" > "$save_path/test_time${start_time}.log"
python -u "../data_collect/my_collect.py" --start-time "$start_time" --end-time "$end_time"