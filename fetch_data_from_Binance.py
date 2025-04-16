import os
import requests
import zipfile
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from tqdm import tqdm
import logging
import shutil

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_kline_data(symbol, interval='1s', start_date=None, end_date=None, output_dir='./data'):
    """
    从Binance下载K线数据并处理（直接按天下载并拼接）
    
    参数:
        symbol (str): 币对名称，如'BTC_USDT'（带下划线）
        interval (str): 时间间隔，如'1s', '1m', '1h'等
        start_date (datetime或str): 起始日期，如果是字符串格式为'YYYY-MM-DD'
        end_date (datetime或str): 结束日期，如果是字符串格式为'YYYY-MM-DD'
        output_dir (str): 输出目录
    
    返回:
        str: 输出文件路径
    """
    # 处理带下划线的交易对格式 - 转换为Binance API格式
    binance_symbol = symbol.replace('_', '')
    
    # 处理字符串日期
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    if isinstance(end_date, str):
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # 默认设置
    if start_date is None:
        start_date = datetime.now() - timedelta(days=7)
    if end_date is None:
        end_date = datetime.now()
        
    # 确保日期对象是naive的（无时区信息）
    if hasattr(start_date, 'tzinfo') and start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
    if hasattr(end_date, 'tzinfo') and end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)
    
    # 创建工作目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建临时下载目录
    temp_dir = f'{output_dir}/temp_{symbol}_{interval}'
    os.makedirs(temp_dir, exist_ok=True)
    
    logger.info(f"开始下载 {symbol} {interval} 数据")
    logger.info(f"下载日期范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    
    # 生成待下载的日期列表
    all_dfs = []
    date_list = []
    
    # 确保生成的日期列表包含所有指定的天
    current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    while current_date <= end_date:
        date_list.append(current_date)
        current_date = current_date + timedelta(days=1)
    
    # 下载每天的数据
    for date in tqdm(date_list, desc=f"下载 {symbol} {interval} 数据"):
        df = download_daily_data(binance_symbol, interval, date, temp_dir)  # 使用转换后的symbol
        if df is not None:
            logger.info(f"成功下载 {date.strftime('%Y-%m-%d')} 的数据，记录数: {len(df)}")
            all_dfs.append(df)
        else:
            logger.warning(f"未能获取 {date.strftime('%Y-%m-%d')} 的数据")
    
    if not all_dfs:
        logger.warning(f"未找到 {symbol} {interval} 的数据")
        # 清理临时目录
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        return None
    
    # 合并数据
    logger.info("合并数据并处理时间格式...")
    merged_df = pd.concat(all_dfs, ignore_index=True)
    
    # 添加列名
    merged_df.columns = [
        "timestamp", "Open", "High", "Low", "Close", "Volume",
        "close_timestamp", "Quote Asset Volume", "Number of Trades",
        "Taker Buy Base Asset Volume", "Taker Buy Quote Asset Volume", "Ignore"
    ]

    # 将数值列转换为适当的类型
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        merged_df[col] = pd.to_numeric(merged_df[col])
    
    # 添加datetime_utc列便于查看
    merged_df["datetime_utc"] = pd.to_datetime(merged_df["timestamp"], unit='ms')
    
    # 排序数据
    merged_df = merged_df.sort_values("timestamp")
    
    # 导出数据 - 使用原始symbol（保留下划线）
    interval_str = interval.replace('s', 'sec').replace('m', 'min').replace('h', 'hour').replace('d', 'day')
    output_file = f'{output_dir}/{symbol}_{interval_str}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv'
    
    merged_df.to_csv(output_file, index=False)
    
    # logger.info(f"数据处理完成: {output_file}")
    # logger.info(f"数据范围: {merged_df['datetime_utc'].min()} 至 {merged_df['datetime_utc'].max()}")
    # logger.info(f"数据条数: {len(merged_df)}")
    
    # 清理临时目录
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    return output_file

def download_daily_data(symbol, interval, date, output_dir):
    """下载每日数据"""
    filename = f'{symbol}-{interval}-{date.strftime("%Y-%m-%d")}'
    url = f'https://data.binance.vision/data/spot/daily/klines/{symbol}/{interval}/{filename}.zip'
    file_path = os.path.join(output_dir, filename + '.csv')
    
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path, header=None)
        except Exception as e:
            logger.warning(f"读取本地文件失败，将重新下载: {str(e)}")
            os.remove(file_path)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        session = requests.Session()
        session.trust_env = False
        
        response = session.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            logger.warning(f'下载失败: {url}, 状态码: {response.status_code}')
            return None
        
        with zipfile.ZipFile(BytesIO(response.content)) as z:
            z.extractall(output_dir)
        
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, header=None)
            
            # 处理可能的微秒级时间戳
            if len(df) > 0 and df[0].max() > 1e13:
                df[0] = df[0] // 1000  # 转换为毫秒
                df[6] = df[6] // 1000  # Close time也要转换
                
            # 显示下载数据的时间范围
            if len(df) > 0:
                min_time = pd.to_datetime(df[0].min(), unit='ms')
                max_time = pd.to_datetime(df[0].max(), unit='ms')
                logger.debug(f"{filename} 时间范围: {min_time} 到 {max_time}")
                
            return df
        else:
            logger.warning(f"解压后未找到文件: {file_path}")
    except Exception as e:
        logger.error(f"下载 {url} 时出错: {str(e)}")
    
    return None

def batch_download_symbols(symbols, interval='1m', start_date=None, end_date=None, base_dir='./data', output_subdir=None):
    """
    批量下载多个交易对的K线数据
    
    参数:
        symbols (list): 交易对列表，如 ['BTC/USDT', 'ETH/USDT']（带斜杠）
        interval (str): 时间间隔，如'1s', '1m', '1h'等
        start_date (str/datetime): 起始日期
        end_date (str/datetime): 结束日期
        base_dir (str): 基础数据目录
        output_subdir (str): 自定义输出子目录名，如果为None则使用默认命名格式
    
    返回:
        tuple: (成功列表, 失败列表, 输出目录)
    """
    # 转换交易对格式：将 'BTC/USDT' 转换为 'BTC_USDT'
    converted_symbols = [symbol.replace('/', '_') for symbol in symbols]
    
    # 处理字符串日期
    if isinstance(start_date, str):
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
    else:
        start_date_obj = start_date
        start_date = start_date_obj.strftime('%Y-%m-%d')
        
    if isinstance(end_date, str):
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
    else:
        end_date_obj = end_date
        end_date = end_date_obj.strftime('%Y-%m-%d')
    
    # 创建输出目录
    if output_subdir:
        # 使用自定义子目录名
        dir_name = f"{base_dir}/{output_subdir}"
    else:
        # 使用默认命名格式
        date_range = f"{start_date.replace('-', '')}_{end_date.replace('-', '')}"
        dir_name = f"{base_dir}/{interval}_{date_range}"
    
    # 确保目录存在
    os.makedirs(dir_name, exist_ok=True)
    
    logger.info(f"开始批量下载 {len(symbols)} 个交易对的数据...")
    
    # 存储成功和失败的交易对
    success_symbols = []
    failed_symbols = []
    
    # 创建临时下载目录
    temp_dir = os.path.join(base_dir, 'temp_download')
    os.makedirs(temp_dir, exist_ok=True)
    
    # 批量下载每个交易对的数据
    for symbol in tqdm(converted_symbols, desc="批量下载进度"):
        try:
            # 设置输出文件路径，文件名保留原始格式（带下划线）
            output_file = os.path.join(dir_name, f"{symbol}.csv")
            
            # 调用下载函数，但需要自定义输出文件
            temp_file = download_kline_data(
                symbol=symbol,  # 保持原始带下划线格式
                interval=interval,
                start_date=start_date_obj,
                end_date=end_date_obj,
                output_dir=temp_dir  # 临时目录
            )
            
            # 如果下载成功，移动文件到最终位置
            if temp_file and os.path.exists(temp_file):
                # 读取数据
                df = pd.read_csv(temp_file)
                # 保存到目标位置
                df.to_csv(output_file, index=False)
                # 删除临时文件
                os.remove(temp_file)
                success_symbols.append(symbol)
                
                # 记录数据统计
                logger.info(f"{symbol}: 成功下载 {len(df)}条记录，时间范围 {df['datetime_utc'].min()} 至 {df['datetime_utc'].max()}")
            else:
                failed_symbols.append(symbol)
        except Exception as e:
            logger.error(f"下载 {symbol} 数据时出错: {str(e)}")
            failed_symbols.append(symbol)
    
    # 清理临时目录
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    
    # 输出下载结果摘要
    print("\n===== 下载完成 =====")
    print(f"成功: {len(success_symbols)}/{len(symbols)}")
    
    if success_symbols:
        print("\n成功下载的交易对:")
        for symbol in success_symbols:
            print(f"  ✅ {symbol}")
    
    if failed_symbols:
        print("\n下载失败的交易对:")
        for symbol in failed_symbols:
            print(f"  ❌ {symbol}")
    
    print(f"\n数据保存在目录: {dir_name}/")
    
    # 如果有成功下载的数据，显示第一个作为示例
    if success_symbols:
        example_symbol = success_symbols[0]
        example_file = os.path.join(dir_name, f"{example_symbol}.csv")
        
        print(f"\n示例数据 ({example_symbol}):")
        df = pd.read_csv(example_file)
        df['datetime_utc'] = pd.to_datetime(df['datetime_utc'])
        
        # 显示每天的数据数量
        print("\n每日数据统计:")
        daily_counts = df.groupby(df['datetime_utc'].dt.date).size()
        for date, count in daily_counts.items():
            print(f"  {date}: {count}条记录")
        
        print(f"\n总数据量: {len(df)}条")
        print(f"时间范围: {df['datetime_utc'].min()} 至 {df['datetime_utc'].max()}")
    
    return success_symbols, failed_symbols, dir_name


###使用示例###
if __name__ == "__main__":
    from configs.ArbConfig import ArbConfig
    config = ArbConfig()

    # 定义需要下载的交易对（带下划线格式）
    symbols = [pair for pair in config.selected_pairs]
    
    # 从配置中获取批量日期并下载
    if hasattr(config, 'batch_test_dates') and config.batch_test_dates:
        print(f"发现{len(config.batch_test_dates)}个日期范围需要下载...")
        
        for start_date, end_date in config.batch_test_dates:
            print(f"\n===== 下载 {start_date} 至 {end_date} 的数据 =====")
            
            success, failed, data_dir = batch_download_symbols(
                symbols=symbols,
                interval=config.interval,
                start_date=start_date,
                end_date=end_date,
                base_dir=config.data_dir,
                output_subdir=f"{config.interval}_{start_date.replace('-', '')}_{end_date.replace('-', '')}"
            )
            
            if success:
                print(f"✅ {start_date}至{end_date}数据下载成功: {len(success)}/{len(symbols)}个交易对")
            else:
                print(f"❌ {start_date}至{end_date}数据下载失败!")
    else:
        # 单一日期下载逻辑(保留原代码)
        success, failed, data_dir = batch_download_symbols(
            symbols=symbols,
            interval=config.interval,
            start_date=config.start_date,
            end_date=config.end_date,
            base_dir=config.data_dir
        )