import backtrader as bt
import os
import logging
import datetime
import json
import matplotlib.pyplot as plt
from typing import List, Optional, Dict, Any
import traceback
import glob
import pandas as pd

from DataManager import DataManager
from tri_arb import TriangularArbStrategy, calculate_arb_paths

# 创建结果目录
RESULTS_DIR = './results'
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

# 创建图表存储目录
PLOTS_DIR = './plots'
if not os.path.exists(PLOTS_DIR):
    os.makedirs(PLOTS_DIR)

class BinanceCommissionInfo(bt.CommInfoBase):
    """Binance交易所手续费模型"""
    params = (
        ('commission', 0.0005),  
        ('maker', 0.0005),      # 挂单手续费
        ('taker', 0.0005),       # 吃单手续费
        ('stocklike', False),
        ('commtype', bt.CommInfoBase.COMM_PERC),  # 百分比手续费
    )
    
    def __init__(self):
        super(BinanceCommissionInfo, self).__init__()
    
    def getcommission(self, size, price, pseudoexec=False):
        """计算手续费"""
        return abs(size) * price * self.p.commission

class TriangleArbBacktest:
    """三角套利回测类"""
    
    def __init__(self, config=None):
        """初始化回测环境"""
        from configs.ArbConfig import ArbConfig
        
        # 基础设置
        self.config = config or ArbConfig()
        
        # 初始化cerebro引擎
        self.cerebro = bt.Cerebro()
        self.cerebro = bt.Cerebro(stdstats=False)
        self.cerebro.broker.set_cash(self.config.initial_cash)
        
        # 设置手续费
        self.commission_info = self.setup_commission()
        self.cerebro.broker.addcommissioninfo(self.commission_info)
        
        # 初始化数据管理器
        self.data_manager = DataManager(self.config)
        
        # 数据加载状态
        self.data_loaded = False
        self.data_count = 0
        self.selected_pairs = None
        self.final_pairs = None
    
    def setup_commission(self):
        """设置手续费模型"""
        commission = BinanceCommissionInfo()
        commission.p.maker = self.config.commission_maker
        commission.p.taker = self.config.commission_taker
        commission.p.commission = self.config.commission_taker  # 使用吃单费率作为默认费率
        return commission
        
    def setup(self, selected_pairs=None):
        """设置回测环境
        
        Args:
            selected_pairs: 指定的交易对列表
            
        Returns:
            bool: 设置是否成功
        """
        # 优先使用传入的交易对列表
        if selected_pairs:
            self.selected_pairs = selected_pairs
            logging.info(f"使用传入的 {len(self.selected_pairs)} 个交易对进行回测")
            return True
        # 其次检查配置文件中的交易对列表
        elif self.config.selected_pairs:
            self.selected_pairs = self.config.selected_pairs
            logging.info(f"使用配置中的 {len(self.selected_pairs)} 个交易对进行回测")
            return True
        
        # 没有足够的信息来设置回测环境
        logging.error("无法设置回测环境: 未提供交易对列表或有效的数据目录")
        return False
        
    def prepare_data(self):
        """准备回测所需的数据
        
        Returns:
            bool: 数据准备是否成功
        """
        if not self.selected_pairs:
            logging.error("未设置交易对，请先调用setup方法")
            return False
        
        # 从config的指定数据目录加载数据
        self.data_loaded = self.data_manager.load_data(
            self.cerebro,
            self.selected_pairs,
            self.config.specific_data_dir
        )
        
        if self.data_loaded:
            self.data_count = len(self.data_manager.loaded_pairs)
            self.final_pairs = self.data_manager.loaded_pairs
            logging.info(f"加载成功，最终可用交易对: {self.data_count} 个")
        else:
            logging.error("数据加载失败")
        
        return self.data_loaded
        
    def run(self):
        """运行回测"""
        if not self.data_loaded:
            logging.error("数据未加载，无法运行回测")
            return None
        # 获取手续费率
        maker_fee = self.commission_info.p.maker
        taker_fee = self.commission_info.p.taker
        # 尝试运行回测
        try:
            # 添加策略
            self.cerebro.addstrategy(
                TriangularArbStrategy,
                fee=taker_fee,
                base_currency=self.config.base_currency,
                trade_amount=self.config.trade_amount,
                threshold=self.config.threshold,
                max_positions=self.config.max_positions,
                skip_seconds=self.config.skip_seconds,
                debug=self.config.debug,
                paths_file=None,
                available_pairs=self.final_pairs
            )
            
            # 记录回测开始
            logging.info(f"开始回测 - "
                        f"基础货币: {self.config.base_currency}, "
                        f"手续费: 挂单 {maker_fee*100:.4f}%, 吃单 {taker_fee*100:.4f}%, "
                        f"套利阈值: {self.config.threshold*100:.4f}%")
            
            start_time = datetime.datetime.now()
            
            # 运行回测
            results = self.cerebro.run()
            strategy = results[0]
            
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            logging.info(f"回测完成，耗时: {duration:.2f} 秒")
            
            # 输出回测结果
            self.print_results(strategy)
            self.export_results(strategy)
            if self.config.plot:
                self.plot()
        
            return strategy
        except Exception as e:
            logging.error(f"回测执行错误: {str(e)}")
            traceback.print_exc()
            return None
        
    def print_results(self, strategy):
        """打印回测结果
        
        Args:
            strategy: 策略对象
        """
        initial = self.config.initial_cash
        final = self.cerebro.broker.getvalue()
        
        logging.info(f"初始资金: {initial:.2f}")
        logging.info(f"最终资金: {final:.2f}")
        logging.info(f"总收益: {final - initial:.2f}")
        logging.info(f"收益率: {(final / initial - 1) * 100:.2f}%")
        
        # 计算回测的日期范围
        start_date = datetime.datetime.strptime(self.config.start_date, '%Y-%m-%d')
        end_date = datetime.datetime.strptime(self.config.end_date, '%Y-%m-%d')
        days = (end_date - start_date).days + 1  # 包含首尾两天
        
        if days > 0:
            # 计算年化收益率
            total_return = final / initial - 1
            annualized_return = (1 + total_return) ** (365 / days) - 1
            logging.info(f"回测周期: {days} 天")
            logging.info(f"年化收益率: {annualized_return * 100:.2f}%")
        
        # 显示策略特定结果
        if hasattr(strategy, 'num_trades'):
            logging.info(f"执行套利次数: {strategy.num_trades}")
        
        if hasattr(strategy, 'total_profit'):
            account_profit = final - initial
            logging.info(f"三角套利理论收益: {strategy.total_profit:.6f}")
            logging.info(f"账户实际变化: {account_profit:.2f}")
            
            if strategy.num_trades > 0:
                logging.info(f"平均每次套利收益: {strategy.total_profit / strategy.num_trades:.6f}")
        
    def export_results(self, strategy):
        """导出回测结果到JSON文件
        
        Args:
            strategy: 策略对象
        """
        try:
            final_value = self.cerebro.broker.getvalue()
            profit = final_value - self.config.initial_cash
            profit_pct = (final_value / self.config.initial_cash - 1) * 100
            
            results = {
                "backtest_summary": {
                    "start_date": self.config.start_date,
                    "end_date": self.config.end_date,
                    "base_currency": self.config.base_currency,
                    "traded_pairs": self.data_count
                },
                "financial_results": {
                    "initial_cash": self.config.initial_cash,
                    "final_value": final_value,
                    "absolute_profit": profit,
                    "percent_profit": profit_pct
                },
                "strategy_results": {
                    "triangle_arb_trades": getattr(strategy, 'num_trades', 0),
                    "total_arb_profit": getattr(strategy, 'total_profit', 0.0)
                },
                "binance_settings": {
                    "maker_fee_pct": self.commission_info.p.maker * 100,
                    "taker_fee_pct": self.commission_info.p.taker * 100,
                    "threshold_pct": self.config.threshold * 100
                },
                "config": self.config.to_dict()
            }
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            threshold_info = f"thresh{self.config.threshold*100:.2f}"
            currency_info = f"{self.config.base_currency}"
            
            filename = f"arb_results_{currency_info}_{threshold_info}_{timestamp}.json"
            filepath = os.path.join(RESULTS_DIR, filename)
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=4)
            
            logging.info(f"回测结果已导出到: {filepath}")
        
        except Exception as e:
            logging.error(f"导出结果时出错: {str(e)}")
            traceback.print_exc()
        
    def plot(self):
        """绘制回测结果图表"""
        if not hasattr(self, 'cerebro') or not self.data_loaded:
            logging.error("无法绘图: 回测未完成")
            return
        
        try:
            # 生成文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"arb_plot_{timestamp}.png"
            plot_file = os.path.join(PLOTS_DIR, filename)
            
            # 设置中文显示（如果需要）
            plt.rcParams['font.sans-serif'] = ['SimHei']
            plt.rcParams['axes.unicode_minus'] = False
            
            # 尝试绘图
            figs = self.cerebro.plot(style='line', 
                                   volume=False,
                                   plotname=f'Binance三角套利 (阈值:{self.config.threshold*100:.2f}%)')
            
            # 保存图片
            if figs and len(figs) > 0:
                figs[0][0].savefig(plot_file, dpi=150)
                logging.info(f"回测图表已保存到: {plot_file}")
                
        except Exception as e:
            logging.error(f"绘制图表时出错: {str(e)}")
            logging.info("注意: 高频数据绘图可能会失败，这不影响回测结果")

def run_backtest(config=None):
    """执行回测的便捷函数
    
    Args:
        config: 配置对象
        
    Returns:
        tuple: (策略对象, 回测对象)
    """
    try:
        # 使用提供的配置或创建默认配置
        if config is None:
            from configs.ArbConfig import ArbConfig
            config = ArbConfig()
        
        # 创建回测实例
        backtest = TriangleArbBacktest(config)
        
        # 设置回测环境
        if not backtest.setup():
            logging.error("回测设置失败")
            return None, backtest
        
        # 准备数据
        if not backtest.prepare_data():
            logging.error("数据准备失败")
            return None, backtest
        
        # 运行回测
        strategy = backtest.run()
        
        return strategy, backtest
        
    except Exception as e:
        logging.error(f"回测执行出错: {str(e)}")
        traceback.print_exc()
        return None, None