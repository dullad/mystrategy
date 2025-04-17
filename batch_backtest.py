import os
import sys
import logging
import datetime
import copy
from configs.ArbConfig import ArbConfig
from backtest import run_backtest
from utils import setup_logging  # 导入工具函数

def limit_memory(max_mem_gb=6):
    """限制程序最大内存使用"""
    max_mem_bytes = max_mem_gb * 1024 * 1024 * 1024  # 转换为字节
    
    # 根据操作系统选择不同的内存限制方法
    if sys.platform.startswith('linux') or sys.platform.startswith('darwin'):
        try:
            import resource
            # 设置软限制和硬限制
            resource.setrlimit(resource.RLIMIT_AS, (max_mem_bytes, max_mem_bytes))
            print(f"内存使用已限制为最大 {max_mem_gb}GB (Linux/macOS)")
        except ImportError:
            print("无法导入resource模块")
        except Exception as e:
            print(f"无法设置内存限制: {e}")
    
    print("请注意手动监控程序内存使用")
    
limit_memory(6)  # 限制为6GB

def run_backtest_for_date(start_date, end_date):
    """针对特定日期范围回测"""
    config = ArbConfig()
    
    # 更新配置中的日期
    config.start_date = start_date
    config.end_date = end_date
    
    # 设置特定数据目录
    date_range = f"{start_date.replace('-', '')}_{end_date.replace('-', '')}"
    config.specific_data_dir = f"{config.data_dir}/{config.interval}_{date_range}"
    
    log_file = setup_logging(start_date, reset_handlers=True)
    print(f"日志记录到: {log_file}")
    logging.info(f"处理日期范围: {start_date} 至 {end_date}")
    logging.info(f"数据目录: {config.specific_data_dir}")
    # 运行回测
    print("\n" + "="*50)
    print(f"回测期间: {start_date} 至 {end_date}")
    print("="*50 + "\n")

    # 显示配置摘要
    from run_backtest import display_config_summary
    display_config_summary(config)
    
    # 执行回测
    start_time = datetime.datetime.now()
    strategy, backtest = run_backtest(config)
    end_time = datetime.datetime.now()
    
    # 显示结果
    if strategy is not None and backtest is not None:
        duration = (end_time - start_time).total_seconds()
        print(f"\n===== {start_date} 至 {end_date} 回测结果 =====")
        print(f"总耗时: {duration:.2f} 秒")
        print(f"初始资金: {config.initial_cash:.2f}")
        print(f"最终资金: {backtest.cerebro.broker.getvalue():.2f}")
        print(f"绝对收益: {backtest.cerebro.broker.getvalue() - config.initial_cash:.2f}")
        print(f"收益率: {(backtest.cerebro.broker.getvalue() / config.initial_cash - 1) * 100:.2f}%")
        
        if hasattr(strategy, 'num_trades'):
            print(f"套利交易次数: {strategy.num_trades}")
    else:
        print(f"\n日期 {start_date} 至 {end_date} 回测失败")
    
    print("="*50 + "\n")
    return strategy, backtest

def main():
    # 创建基础配置
    bas_config = ArbConfig()
    date_ranges = bas_config.batch_test_dates
    print(f"将对{len(date_ranges)}个日期范围进行回测")

    # 存储所有回测结果
    results = {}
    
    # 执行每个日期的回测
    for start_date, end_date in date_ranges:
        strategy, backtest = run_backtest_for_date(start_date, end_date)
        if backtest is not None:
            results[(start_date, end_date)] = (strategy, backtest)
    # 显示所有结果的汇总
    if len(results) > 0:
        print("\n=========== 全部回测结果汇总 ===========")
        for (start_date, end_date), (strategy, backtest) in results.items():
            if backtest is not None:
                profit = backtest.cerebro.broker.getvalue() - bas_config.initial_cash
                profit_pct = (profit / bas_config.initial_cash) * 100
                num_trades = getattr(strategy, 'num_trades', 0)
                print(f"{start_date} 至 {end_date}: 收益 {profit:.2f} ({profit_pct:.2f}%), 交易 {num_trades} 次")
        print("=========================================\n")

if __name__ == "__main__":
    main()