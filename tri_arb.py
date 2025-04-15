import backtrader as bt
import networkx as nx
import logging
import time
import datetime
import pandas as pd
import os
import json

# 设置日志
arb_logger = logging.getLogger('tri_arb')
# 保存路径的目录
ARB_PATHS_DIR = "arb_paths"
if not os.path.exists(ARB_PATHS_DIR):
    os.makedirs(ARB_PATHS_DIR)
# 保存交易记录的目录
TRADES_DIR = "./trades"
if not os.path.exists(TRADES_DIR):
    os.makedirs(TRADES_DIR)

def build_currency_graph(pairs):
    """构建币种交易对图结构"""
    graph = nx.DiGraph()
    for pair in pairs:
        try:
            if '/' in pair:
                pair = pair.replace('/', '_')
            base, quote = pair.split('_')
            # 添加正向和反向边
            graph.add_edge(base, quote, symbol=pair, direction=1)  # 卖出方向
            graph.add_edge(quote, base, symbol=pair, direction=-1) # 买入方向
        except Exception as e:
            arb_logger.error(f"解析交易对 {pair} 出错: {str(e)}")
    return graph

def find_triangular_paths(graph, base_currency):
    """使用NetworkX高效查找三角套利路径
    
    Args:
        graph: 币种交易图
        base_currency: 基础货币，如'USDT'
        
    Returns:
        list: 套利路径列表
    """
    triangles = []
    if base_currency not in graph:
        arb_logger.warning(f"警告: 基础货币 {base_currency} 不在交易图中!")
        return triangles
 
    # 统计可能的中间货币数量
    mid_currencies = list(graph.successors(base_currency))
    if not mid_currencies:
        arb_logger.error(f"错误: 没有从 {base_currency} 出发的交易对，无法构建套利路径。")
        return triangles
    arb_logger.info(f"找到 {len(mid_currencies)} 个可作为中间货币的币种")

    # 查找所有简单循环 - 长度为3
    for mid in mid_currencies:
        for end in graph.successors(mid):
            if end != base_currency and end != mid and base_currency in graph.successors(end):
                path = [
                    (graph[base_currency][mid]['symbol'], graph[base_currency][mid]['direction']),
                    (graph[mid][end]['symbol'], graph[mid][end]['direction']),
                    (graph[end][base_currency]['symbol'], graph[end][base_currency]['direction'])
                ]
                triangles.append(path)

    arb_logger.info(f"找到 {len(triangles)} 条以 {base_currency} 为起点和终点的三角套利路径")
    return triangles

def save_paths_to_file(paths, required_pairs, base_currency, file_name=None, calculation_time=None):
    """将套利路径保存到文件中
    
    Args:
        paths: 套利路径列表
        base_currency: 基础货币名称
        required_pairs: 所需的交易对列表
        file_name: 可选，文件名（不包含路径）
        calculation_time: 可选，计算路径所花费的时间（毫秒）
    
    Returns:
        str: 保存的文件路径
    """
    if file_name is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"arb_paths_{base_currency}_{timestamp}.txt"
    
    file_path = os.path.join(ARB_PATHS_DIR, file_name)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        # 写入元数据
        f.write(f"# 三角套利路径 - 基础货币: {base_currency}\n")
        f.write(f"# 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 路径数量: {len(paths)}\n")
        if calculation_time is not None:
            f.write(f"# 计算耗时: {calculation_time:.2f}毫秒\n")
        f.write("\n")
        
        # 写入路径数据
        for i, path in enumerate(paths):
            path_str = " → ".join([f"{pair}({'+' if dir==1 else '-'})" for pair, dir in path])
            f.write(f"路径{i+1}: {path_str}\n")
        # 写入所需交易对列表
        f.write("\n# 所需交易对列表\n")
        f.write(", ".join([f'"{pair}"' for pair in required_pairs]))
        f.write("\n")

        # 写入机器可读的JSON格式
        f.write("\n# JSON格式路径数据 (用于程序读取)\n")
        f.write(json.dumps(paths))
    
    return file_path

def load_paths_from_file(file_path):
    """从文件中加载套利路径
    
    Args:
        file_path: 套利路径文件的路径
        
    Returns:
        list: 套利路径列表
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # 查找JSON数据部分
        json_start = content.find("[[[")
        if json_start > -1:
            json_data = content[json_start:]
            try:
                paths = json.loads(json_data)
                return paths
            except json.JSONDecodeError:
                arb_logger.error(f"从文件 {file_path} 解析JSON数据失败")
    
    arb_logger.error(f"无法从文件 {file_path} 加载套利路径")
    return []

def calculate_arb_paths(pairs, base_currency, save_to_file=True):
    """计算套利路径并可选保存到文件
    
    Args:
        pairs: 交易对列表
        base_currency: 基础货币
        save_to_file: 是否保存到文件
        
    Returns:
        tuple: (套利路径列表, 文件路径(如果保存了))
    """
    start_time = time.time()
    
    # 确保使用下划线格式
    formatted_pairs = [pair.replace('/', '_') if '/' in pair else pair for pair in pairs]
    
    # 创建完整的图用于最终验证
    graph = build_currency_graph(formatted_pairs)
    arb_logger.info(f"总图构建完成: {len(graph.nodes())} 个节点, {len(graph.edges())} 条边")
    
    all_paths = find_triangular_paths(graph, base_currency)
    
    calculation_time = (time.time() - start_time) * 1000
    arb_logger.info(f"路径计算完成，耗时 {calculation_time:.2f} 毫秒")
    arb_logger.info(f"共找到 {len(all_paths)} 条套利路径")

    required_pairs = extract_required_pairs(all_paths)

    file_path = None
    if save_to_file and all_paths:
        file_path = save_paths_to_file(all_paths, required_pairs, base_currency, calculation_time=calculation_time)
        arb_logger.info(f"套利路径已保存到文件: {file_path}")
        # 输出路径示例
        for i, path in enumerate(all_paths[:3]):
            if i >= 3:
                break
            path_str = " → ".join([f"{pair}({'+' if dir==1 else '-'})" for pair, dir in path])
            arb_logger.info(f"路径示例{i+1}: {path_str}")
    
    
    return all_paths, file_path, required_pairs

def extract_required_pairs(paths):
    """从套利路径中提取所需的交易对"""
    required_pairs = set()
    for path in paths:
        for pair, _ in path:
            required_pairs.add(pair)
    required_pairs_list = list(required_pairs)
    arb_logger.info(f"路径所需 {len(required_pairs_list)} 个交易对")
    return required_pairs_list

class TriangularArbStrategy(bt.Strategy):
    """三角套利策略"""
    params = dict(
        fee=0.0005,            # 交易手续费
        base_currency='USDT',  # 基础货币
        trade_amount=0.1,      # 每次固定交易0.1个基础货币
        threshold=0.001,       # 收益阈值 (0.1%)，超过此值才执行交易
        max_positions=5,       # 最大同时持有的套利路径数
        skip_seconds=3,        # 跳过的秒数
        debug=False,           # 是否开启调试模式
        paths_file=None,       # 套利路径文件路径
        save_paths=True,       # 是否保存计算的路径到文件
        available_pairs=None,  # 可用的交易对列表
    )

    def __init__(self):
        """初始化策略"""
        self.arb_paths = [] 
        self.pairs = []
        self.active_trades = set()
        self.execution_times = []
        self.num_trades = 0
        self.total_profit = 0.0
        self.last_trade_time = None
        self.skip_until = None
        self.trade_records = []
        self.paths_file_path = None

        if self.p.available_pairs:
            # 如果提供了可用交易对列表，则使用它
            self.pairs = self.p.available_pairs
            self.log(f"使用提供的 {len(self.pairs)} 个交易对")
        else:
            # 否则从datas中获取
            self.pairs = [d._name for d in self.datas]
            self.log(f"从数据中获取 {len(self.pairs)} 个交易对")
        
        # 计算套利路径 - 始终使用实际可用的交易对
        if self.p.paths_file:
            # 从文件加载套利路径
            self.log(f"从文件加载套利路径: {self.p.paths_file}")
            self.arb_paths = load_paths_from_file(self.p.paths_file)
            self.log(f"从文件加载了 {len(self.arb_paths)} 条套利路径")
            self.paths_file_path = self.p.paths_file
        else:
            self.log("基于实际可用交易对计算套利路径...")
            self.arb_paths, file_path, _ = calculate_arb_paths(
                self.pairs, 
                self.p.base_currency,
                save_to_file=self.p.save_paths
            )
            if file_path:
                self.log(f"套利路径已保存到: {file_path}")
                self.paths_file_path = file_path

        if self.arb_paths:
            self.log(f"找到 {len(self.arb_paths)} 个套利路径")
            if len(self.arb_paths) > 0 and self.p.debug:
                for i, path in enumerate(self.arb_paths[:3]):
                    path_str = " → ".join([f"{pair}({'+' if dir==1 else '-'})" for pair, dir in path])
                    self.log(f"路径示例{i+1}: {path_str}")
        else:
            self.log(f"没有找到符合要求的套利路径")
        
    def next(self):
        """主策略逻辑"""
        if not hasattr(self, 'arb_paths') or not self.arb_paths:
            return
        
        start_time = time.time()
        # 检查是否需要跳过当前时间点
        current_datetime = self.datas[0].datetime.datetime(0)
        if self.skip_until and current_datetime < self.skip_until:
            return
        
        # 获取可用资金和可执行交易数量
        total_available_cash = self.broker.getcash()
        per_trade_amount = self.p.trade_amount
        max_positions = self.p.max_positions
        max_possible_trades = min(max_positions, int(total_available_cash / per_trade_amount))
        
        if max_possible_trades <= 0:
            return
        
        profitable_paths = self._check_paths_chunk(self.arb_paths, per_trade_amount)
        if not profitable_paths:
            return
        profitable_paths.sort(reverse=True, key=lambda x: x[0])
        executed_count = 0
        
        for profit, path in profitable_paths[:max_possible_trades]:
            path_id = hash(str(path))
            if path_id in self.active_trades:
                continue
                
            self.active_trades.add(path_id)
            self._execute_trade(path, per_trade_amount, path_id, profit)
            executed_count += 1
        
        if executed_count > 0:
            self.last_trade_time = current_datetime
            self.skip_until = current_datetime + datetime.timedelta(seconds=self.p.skip_seconds)
        
        # 记录执行时间
        execution_time = (time.time() - start_time) * 1000  # 转换为毫秒
        self.execution_times.append(execution_time)
    
    def _check_paths_chunk(self, paths, amount):
        """检查一组路径是否有利可图
        
        Args:
            paths: 路径列表
            amount: 交易金额
            
        Returns:
            list: 包含(利润, 路径)元组的列表
        """
        profitable = []
        # max_profit = -float('inf')
        for path in paths:
            path_id = hash(str(path))
            if path_id in self.active_trades:
                continue
            
            profit = self._calculate_profit(path, amount)
            # max_profit = max(max_profit, profit) if profit != -1 else max_profit

            # path_str = " → ".join([f"{pair}({'+' if dir==1 else '-'})" for pair, dir in path])
            prices = []
            for pair, direction in path:
                price = self.getprice(pair)
                if price:
                    prices.append(f"{pair}:{price:.8f}")
                else:
                    prices.append(f"{pair}:NA")
            # self.log(f"检查路径: {path_str} - 汇率: {', '.join(prices)} - 利润率: {profit*100:.6f}%")        

            if profit > self.params.threshold:
                profitable.append((profit, path))

        return profitable
    
    def getprice(self, pair_name):
        """获取交易对的当前价格"""
        for data in self.datas:
            if data._name == pair_name:
                return data.close[0]
        return None

    def _calculate_profit(self, path, amount):
        """计算套利路径的理论收益率"""
        base_currency = self.p.base_currency
        initial = amount
        current = amount
        current_currency = base_currency

        for pair, direction in path:
            price = self.getprice(pair)
            if not price:
                return -1  # 无效价格
            
            base, quote = pair.split('_')

            if direction == 1:
                if current_currency == base:
                    # 卖出基础货币
                    current = current * price * (1 - self.params.fee)
                    current_currency = quote
                else:
                    return -1  # 货币不匹配
            else:
                if current_currency == quote:
                    # 买入基础货币
                    current = (current / price) * (1 - self.params.fee)
                    current_currency = base
                else:
                    return -1  # 货币不匹配
        
        if current_currency != base_currency:
            return -1
        return (current - initial) / initial
    
    def _execute_trade(self, path, amount, path_id, profit):
        """执行套利交易
        
        Args:
            path: 交易路径
            amount: 交易金额
            path_id: 路径ID
            profit: 预期收益率
        """
        prices = []
        currency_pairs = []
        total_fee = 0.0
        fee_amounts = []
        
        # 获取交易对价格
        for pair, direction in path:
            price = self.getprice(pair)
            prices.append(price)
            
            if direction == 1:
                currency_pairs.append(pair)
            else:
                base, quote = pair.split('_')
                currency_pairs.append(f"{quote}_{base}")

        # 获取当前时间
        current_datetime = self.datas[0].datetime.datetime(0)
        initial_amount = self.broker.getvalue()
        
        try:
            current_amount = amount
            current_currency = self.p.base_currency

            for i, (pair, direction) in enumerate(path):
                price = self.getprice(pair)
                base_currency, quote_currency = pair.split('_')

                if direction == 1:
                    if current_currency == base_currency:
                        size = current_amount
                        fee_amount = size * price * self.params.fee
                        fee_amounts.append(f"{fee_amount:.6f} {quote_currency}")
                        total_fee += fee_amount
                        # 虚拟执行交易，不使用backtrader自带的交易系统
                        current_amount = size * price - fee_amount
                        current_currency = quote_currency
                    else:
                        raise ValueError(f"货币不匹配: 当前持有{current_currency}，但需要卖出{base_currency}")
                else:
                    if current_currency == quote_currency:
                        size = current_amount / price
                        fee_amount = size * self.params.fee
                        fee_amounts.append(f"{fee_amount:.6f} {base_currency}")
                        total_fee += fee_amount * price 
                        # 虚拟执行交易
                        current_amount = size - fee_amount
                        current_currency = base_currency
                    else:
                        raise ValueError(f"货币不匹配: 当前持有{current_currency}，但需要使用{quote_currency}")
                    
            if current_currency != self.p.base_currency:
                raise ValueError(f"套利交易未能回到基础货币: 当前持有{current_currency}")

            final_amount = initial_amount - amount + current_amount
            self.broker.setcash(final_amount)  # 更新账户余额

            actual_profit = final_amount - initial_amount
            profit_rate = actual_profit / amount
            self.total_profit += actual_profit
            self.num_trades += 1

            # 构建路径描述字符串
            path_str = " → ".join([f"{pair}({'+' if dir==1 else '-'})" for pair, dir in path])
            
            # 将交易记录添加到列表中
            self.trade_records.append({
                'datetime': current_datetime,
                'path': path_str,
                'profit_rate': profit_rate, 
                'amount': amount,
                'final_amount': current_amount
            })

            # 格式化输出
            rates = []
            for i, (pair, direction) in enumerate(path):
                if direction == 1:
                    rates.append(f"{prices[i]:.8f}")
                else:
                    rates.append(f"1/{prices[i]:.8f}")
            
            self.log(f"执行套利：{' → '.join([cp for cp in currency_pairs])}; "
                    f"汇率: {', '.join(rates)}; "
                    f"收益率: {profit_rate*100:.4f}%; "
                    f"资产: {final_amount:.4f}")
            
        except Exception as e:
            self.log(f"执行套利交易失败: {str(e)}")
        finally:
            self.active_trades.remove(path_id)

    def log(self, txt, dt=None):
        """日志记录"""
        dt = dt or self.datas[0].datetime.datetime(0)
        arb_logger.info(f"{dt.isoformat()} {txt}")
    
    def stop(self):
        """策略结束时执行 - 输出性能统计和总结"""
        if self.execution_times:
            avg_time = sum(self.execution_times) / len(self.execution_times)
            max_time = max(self.execution_times)
            
            self.log(f"策略完成: 共检查{len(self.arb_paths)}条路径, "
                    f"执行{self.num_trades}次套利, 总收益:{self.total_profit:.4f}")
            self.log(f"性能统计: 平均每轮耗时={avg_time:.2f}ms, 最长耗时={max_time:.2f}ms")
            
            if self.trade_records:
                self.export_trade_records()
        else:
            self.log("策略执行完成，但未进行任何套利交易。")

    def export_trade_records(self):
        """将交易记录导出到Excel文件"""
        if not self.trade_records:
            self.log("没有交易记录可导出")
            return
        try:
            # 创建DataFrame
            df = pd.DataFrame(self.trade_records)
            df['datetime'] = df['datetime'].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S'))
            df = df.sort_values('datetime')
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            threshold_info = f"thresh{self.params.threshold*100:.2f}"
            filename = f"arb_trades_{self.params.base_currency}_{threshold_info}_{timestamp}.xlsx"
            filepath = os.path.join(TRADES_DIR, filename)
            
            # 将DataFrame保存为Excel文件
            df.to_excel(filepath, index=False)
            self.log(f"交易记录已导出到: {filepath}")
        except Exception as e:
            self.log(f"导出交易记录时出错: {str(e)}")