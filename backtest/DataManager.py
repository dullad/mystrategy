import os
import glob
import logging
import pandas as pd
import backtrader as bt
from typing import List, Dict, Optional
from datetime import datetime

class DataManager:
    """数据管理类，负责加载和管理回测数据"""
    
    def __init__(self, config):
        """初始化数据管理器"""
        self.config = config
        self.data_dir = config.data_dir
        self.specific_data_dir = config.specific_data_dir
        self.available_currencies = set()
        self.loaded_pairs = []
        self.data_feeds = {}  # 存储加载的数据
    
    def load_data(self, cerebro: bt.Cerebro, pairs: List[str], data_dir: str = None) -> bool:
        """加载数据到Backtrader
        
        Args:
            cerebro: Backtrader实例
            pairs: 需要加载的交易对(下划线格式)
            data_dir: 可选的数据目录，如果不提供则使用self.data_dir
            
        Returns:
            bool: 是否成功加载足够数据
        """
        if data_dir:
            self.data_dir = data_dir
            
        data_files = glob.glob(os.path.join(self.data_dir, "*.csv"))
        if not data_files:
            logging.error(f"在 {self.data_dir} 目录中没有找到CSV文件")
            return False
            
        logging.info(f"找到 {len(data_files)} 个数据文件")
        
        # 设置时间范围
        start_time = datetime.strptime(f"{self.config.start_date} 00:00:00", "%Y-%m-%d %H:%M:%S")
        end_time = datetime.strptime(f"{self.config.end_date} 23:59:59", "%Y-%m-%d %H:%M:%S")
        logging.info(f"使用时间范围: {start_time} 到 {end_time} (UTC)")
        
        # 过滤匹配的文件
        selected_files = []
        for pair in pairs:
            matching_files = [f for f in data_files 
                              if os.path.splitext(os.path.basename(f))[0] == pair 
                              or pair + ".csv" == os.path.basename(f)]  # 匹配带扩展名的情况
            if matching_files:
                selected_files.extend(matching_files)
            else:
                logging.warning(f"未找到交易对 {pair} 的数据文件")
        
        logging.info(f"找到 {len(selected_files)}/{len(pairs)} 个需求交易对的数据文件")
        
        # 加载数据
        loaded_count = 0
        self.available_currencies = set()
        self.loaded_pairs = []
        
        # 清空之前的数据
        self.data_feeds.clear()
        
        for file_path in selected_files:
            try:
                # 从文件名提取交易对
                file_name = os.path.basename(file_path)
                file_name_without_ext = os.path.splitext(file_name)[0]
                symbol_parts = file_name_without_ext.split('_')[:2]
                pair_name = f"{symbol_parts[0]}_{symbol_parts[1]}"
                
                # 读取CSV文件
                df = pd.read_csv(file_path)
                
                # 添加货币到可用列表
                self.available_currencies.add(symbol_parts[0])
                self.available_currencies.add(symbol_parts[1])
                
                # 重命名列以匹配backtrader要求
                if 'Open' in df.columns:
                    df.rename(columns={
                        'Open': 'open',
                        'High': 'high', 
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume'
                    }, inplace=True)
                
                # 确保有正确的datetime列
                if 'datetime_utc' in df.columns:
                    df['datetime'] = pd.to_datetime(df['datetime_utc'])
                else:
                    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
                
                # 创建数据源
                data = bt.feeds.PandasData(
                    dataname=df,
                    datetime='datetime',
                    open='open',
                    high='high',
                    low='low',
                    close='close',
                    volume='volume',
                    name=pair_name,  # 使用下划线格式作为名称
                    timeframe=bt.TimeFrame.Seconds,
                    compression=1
                )
                
                # 添加到cerebro
                cerebro.adddata(data)
                self.loaded_pairs.append(pair_name)
                self.data_feeds[pair_name] = data
                
                loaded_count += 1
                logging.info(f"加载 {pair_name} 数据，共 {len(df)} 条记录")
                
            except Exception as e:
                logging.error(f"处理文件 {file_path} 时出错: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # 验证是否加载了足够数据
        if loaded_count < 3:  # 至少需要三个交易对才能形成套利三角形
            logging.error(f"加载的交易对数量不足，无法形成三角形套利! 只加载了 {loaded_count} 个交易对")
            return False
            
        # 检查基础货币是否存在
        if self.config.base_currency not in self.available_currencies:
            logging.error(f"基础货币 {self.config.base_currency} 不在任何交易对中! 可用货币: {sorted(self.available_currencies)}")
            return False
            
        logging.info(f"成功加载 {loaded_count} 个数据集")
        return loaded_count >= 3

    @staticmethod
    def convert_to_underscore_format(pair: str) -> str:
        """将斜杠格式转换为下划线格式
        
        Args:
            pair: 斜杠格式的交易对 (如 "BTC/USDT")
            
        Returns:
            str: 下划线格式的交易对 (如 "BTC_USDT")
        """
        return pair.replace('/', '_')