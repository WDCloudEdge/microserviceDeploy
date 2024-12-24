import pandas as pd
import os
import glob

# 修改需要处理的文件夹路径，每个用户数请求持续的时间，一共几种用户数量
to_be_handled_directory = r'E:\research\my_deployment\data_collect\wcx_1733831668'
fre = '0.2T'
users_num = 8

# 查找当前目录下所有的 .csv 文件
csv_files = glob.glob(os.path.join(to_be_handled_directory, '*.csv'))

# 遍历每个 .csv 文件
for csv_file in csv_files:
    # 提取文件名（去掉扩展名）
    file_name = os.path.splitext(os.path.basename(csv_file))[0]
    
    # 创建一个与文件名同名的文件夹
    folder_path = os.path.join(to_be_handled_directory, file_name)
    
    # 如果文件夹不存在，则创建它
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"文件夹 '{folder_path}' 已创建")
    else:
        print(f"文件夹 '{folder_path}' 已存在")


    # 读取 CSV 文件
    df = pd.read_csv(csv_file)

    # 确保时间列是 datetime 类型
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y/%m/%d %H:%M')
    
    # 获取最后一列的第二行和最后一行作为开始时间和结束时间
    start_time = df['timestamp'].iloc[1]  # 第二行的时间为开始时间
    end_time = df['timestamp'].iloc[-1]   # 最后一行的时间为结束时间
    end_time = pd.date_range(start=end_time, periods=2, freq=fre)[-1] 
    # # 筛选出包含 cpu_usage 的列
    # cpu_columns = [col for col in df.columns if 'cpu_usage' in col]
    # df_cpu = df[['timestamp'] + cpu_columns]

    # 生成每5分钟的时间区间
    time_intervals = pd.date_range(start=start_time, end=end_time, freq=fre)

    # 按时间区间分割数据并保存为 CSV 文件
    for i in range(len(time_intervals) - 1):
        # 获取当前时间段的开始和结束时间
        interval_start = time_intervals[i]
        interval_end = time_intervals[i + 1]

        # 筛选出当前时间段的数据
        df_segment = df[(df['timestamp'] >= interval_start) & (df['timestamp'] < interval_end)]

        # 如果该时间段有数据，保存为 CSV 文件
        if not df_segment.empty:
            filename = f'{file_name}{(i+1)*100}.csv'
            path = os.path.join(folder_path, filename)
            df_segment.to_csv(path, index=False)
            print(f'Saved {filename}')
    average_results = []

    # 遍历0.csv到8.csv
    for i in range(users_num):
        # 构造文件名
        average_filename = f'{file_name}{(i + 1) * 100}.csv'
        file_path = os.path.join(folder_path, average_filename)
        # 如果文件存在，则处理
        if os.path.exists(file_path):
            # 读取 CSV 文件
            df = pd.read_csv(file_path)
            
            # 计算每列的平均值（排除timestamp列）
            avg_values = df.drop(columns=['timestamp']).mean()
            
            # 将结果添加到结果列表
            avg_values['users'] = (i + 1) * 100  # 添加文件名列
            average_results.append(avg_values)

            # 将结果转换为DataFrame
            average_df = pd.DataFrame(average_results)

            # 保存为一个新的 CSV 文件
            output_file = os.path.join(folder_path, f'{average_filename}_average_results.csv')
            average_df.to_csv(output_file, index=False)

            print(f"平均值结果已保存到 '{output_file}'")
