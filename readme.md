# 需要修改的路径变量
1. load-generate\auto.sh:save_path：locust执行结果保存路径
2. data_collect\my_collect.py：data_folder Prometheus收集的数据保存路径
3. placement\placement_result.py:①file_path结果转换为hipster的部署yaml保存位置,②result_path微服务部署位置的csv文件
4. algorithms\RSDQL\train.py:file_path部署结果csv保存位置
# wcx目前写了的如何运行
## 发负载和数据收集
执行load-generate\auto.sh，会按照文件里的模式发负载，负载结束后会收集数据到路径变量1和2
负载模式：auto.sh是用户的负载，data_collect\my_collect.py是不同请求组合的负载
## RSDQL怎么复现，以hipster为例
1. 执行algorithms\RSDQL\train.py文件，结果保存在'placement\service&placement.csv'，
2. 执行placement\placement_result.py，得到最终的yaml文件路径变量3