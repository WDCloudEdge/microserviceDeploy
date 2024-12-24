import yaml
import pandas as pd
import time
# 读取 YAML 文件

al_name = 'Random'
timestamp = str(int(time.time()))
# 将修改后的数据写回 YAML 文件
file_path = f'E:/research/experiment/experiment_data/baseline/RSDQL/deployment_{al_name}_{timestamp}.yaml'
result_path = 'E:/research/experiment/experiment_data/baseline/RSDQL/service&placement_RSDQL_1734597460.csv'
with open('./hipster.yaml', 'r') as file:
    data = list(yaml.safe_load_all(file))  # 使用 safe_load_all 并转成列表

    # 打印读取的 YAML 数据，确认文件是否正确读取
    print("Original YAML data:")
    print(data)

    # 读取 CSV 文件
    result_df = pd.read_csv(result_path, header=None, skiprows=1)
    
    # 调试打印 CSV 文件的内容
    print("CSV Data:")
    print(result_df)

    # 开始修改 YAML 数据
    for index, row in result_df.iterrows():
        name = row[0]
        node = row[1]
        
        # 查找并修改 nodeSelector
        modified = False  # 标记是否做了修改
        for item in data:
            if isinstance(item, dict) and item.get('kind') == 'Deployment' and item.get('metadata', {}).get('name') == name:
                # 找到匹配项并修改 nodeSelector
                if 'spec' in item and 'template' in item['spec']:
                    if 'spec' in item['spec']['template'] and 'nodeSelector' in item['spec']['template']['spec']:
                        item['spec']['template']['spec']['nodeSelector']['kubernetes.io/hostname'] = node
                        modified = True
                        break

        # 打印每次修改后的标记，确认是否真的修改了
        if modified:
            print(f"Modified Deployment: {name} to node: {node}")
        else:
            print(f"No modification needed for Deployment: {name}")
    
    with open(file_path, 'w') as file:
        yaml.dump_all(data, file, default_flow_style=False, allow_unicode=True)  # 使用 dump_all 来写回多个文档
        print("YAML file written successfully.")
