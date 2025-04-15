import os
import glob
import pandas as pd
import random
from typing import List, Dict, Tuple, Optional

from configs.ArbConfig import ArbConfig
from backtest.tri_arb import calculate_arb_paths

def analyze_liquidity(config: ArbConfig) -> List[str]:
    """分析指定目录下所有交易对的流动性，返回流动性最好的前X%交易对"""
    data_files = glob.glob(os.path.join(config.specific_data_dir, "*.csv"))
    if not data_files:
        print(f"在指定目录 {config.specific_data_dir} 中未找到CSV文件")
        return False
    
    # 从文件名提取交易对并分析流动性
    all_available_pairs = []
    pair_liquidity = {}  # 存储交易对和对应的流动性指标
    
    print(f"开始分析 {len(data_files)} 个交易对的流动性...")
    print(f"流动性评分权重: 成交量 {config.liquidity_volume_weight:.2f}, 交易次数 {config.liquidity_trades_weight:.2f}")
    
    sample_size = 5000
    sample_indices = None
    read_indices = None

    for i, file_path in enumerate(data_files):
        file_name = os.path.basename(file_path)
        file_name_without_ext = os.path.splitext(file_name)[0]
        if '_' in file_name_without_ext:
            pair = file_name_without_ext
            # 只读取部分数据以提高性能
            if i == 0 or  sample_indices is None:
                with open(file_path, 'r') as f:
                    total_rows = sum(1 for _ in f) - 1  # 减去标题行
                sample_indices = sorted(random.sample(range(1, total_rows + 1), sample_size))
                read_indices = [0] + sample_indices
            df = pd.read_csv(file_path, skiprows=lambda x: x not in read_indices)
            avg_volume = df['Volume'].mean()
            avg_trades = df['Number of Trades'].mean() if 'Number of Trades' in df.columns else 0
            liquidity_score = (config.liquidity_volume_weight * avg_volume) + \
                                (config.liquidity_trades_weight * avg_trades)
            pair_liquidity[pair] = liquidity_score
            all_available_pairs.append(pair)
                
    if not all_available_pairs:
        print("未能从数据目录提取任何交易对")
        return []
    print(f"共分析了 {len(all_available_pairs)} 个交易对的流动性")
    sorted_pairs = sorted(pair_liquidity.items(), key=lambda x: x[1], reverse=True)
    top_count = max(config.liquidity_min_pairs, int(len(sorted_pairs) * config.liquidity_top_percent))
    top_pairs = [pair for pair, _ in sorted_pairs[:top_count]]
    print(f"筛选出流动性最好的前{config.liquidity_top_percent*100:.0f}%交易对，共 {len(top_pairs)} 个")
    print(f"计算三角套利路径，基础货币: {config.base_currency}")
    _, _, required_pairs = calculate_arb_paths(
        top_pairs, 
        config.base_currency, 
        save_to_file=True
    )
    if not required_pairs:
        print("未能计算出任何套利路径")
        return False
    selected_pairs = required_pairs
    print(f"计算得到 {len(selected_pairs)} 个三角套利所需的交易对")
    return selected_pairs

def main():
    # 加载配置
    config = ArbConfig()
    selected_pairs = analyze_liquidity(config)
    if selected_pairs:
        print(f"数据处理完成，得到 {len(selected_pairs)} 个交易对")
        print(f"交易对列表: {', '.join(selected_pairs[:5])}...")
        print(f"可将此列表添加到配置文件的selected_pairs字段")
        
if __name__ == "__main__":
    main()