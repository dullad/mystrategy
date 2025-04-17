import os
import sys
import logging
import datetime
from utils import setup_logging  # 导入工具函数

# 导入配置和回测模块
from configs.ArbConfig import ArbConfig
from backtest import run_backtest

def display_config_summary(config: ArbConfig):
    """显示配置摘要"""
    print("\n===== 回测配置摘要 =====")
    print(f"基础货币: {config.base_currency}")
    print(f"初始资金: {config.initial_cash}")
    print(f"套利阈值: {config.threshold*100:.4f}%")
    print(f"回测期间: {config.start_date} 至 {config.end_date}")
    print(f"数据间隔: {config.interval}")
    print(f"手续费率: 挂单 {config.commission_maker*100:.4f}%, 吃单 {config.commission_taker*100:.4f}%")
    print(f"数据目录: {config.specific_data_dir}")
    print(f"是否下载: {'是' if config.download_data else '否'}")
    
    # 显示交易对信息
    if config.selected_pairs:
        print(f"指定交易对: {len(config.selected_pairs)} 个")
        if len(config.selected_pairs) <= 5:
            print(f"交易对列表: {', '.join(config.selected_pairs)}")
        else:
            print(f"交易对列表(前5个): {', '.join(config.selected_pairs[:5])}...")
    else:
        print("交易对: 自动计算")
    
    print("=========================\n")

def main():
    config = ArbConfig()

    date_str = config.start_date.replace('-', '')
    log_file = setup_logging(date_str)
    print(f"日志记录到: {log_file}")

    display_config_summary(config)
    
    logging.info("开始执行回测...")
    start_time = datetime.datetime.now()
    
    strategy, backtest = run_backtest(config)
    
    end_time = datetime.datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 显示结果摘要
    if strategy is not None and backtest is not None:
        print("\n===== 回测结果摘要 =====")
        print(f"总耗时: {duration:.2f} 秒")
        print(f"初始资金: {config.initial_cash:.2f}")
        print(f"最终资金: {backtest.cerebro.broker.getvalue():.2f}")
        print(f"绝对收益: {backtest.cerebro.broker.getvalue() - config.initial_cash:.2f}")
        print(f"收益率: {(backtest.cerebro.broker.getvalue() / config.initial_cash - 1) * 100:.2f}%")
        
        if hasattr(strategy, 'num_trades'):
            print(f"套利交易次数: {strategy.num_trades}")
        
        print("完整结果已保存到results目录")
        print("=========================\n")
    else:
        print("\n回测执行失败，请查看日志了解详情。")
    
    del strategy
    del backtest
    import gc
    gc.collect()

if __name__ == "__main__":
    main()