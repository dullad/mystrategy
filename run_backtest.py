import os
import sys
import logging
import datetime

# 设置日志
log_dir = './logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f'{log_dir}/backtest_{timestamp}.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

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
    display_config_summary(config)
    # 询问用户是否继续
    if sys.stdout.isatty():  # 如果是交互式终端
        user_input = input("确认开始回测? (y/n): ")
        if user_input.lower() not in ['y', 'yes']:
            print("已取消回测。")
            return
    
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

if __name__ == "__main__":
    print(f"日志记录到: {log_file}")
    main()