import os
import logging
import datetime

def setup_logging(date_str=None, reset_handlers=False):
    """
    设置日志
    
    Args:
        date_str: 日期字符串，用于日志文件名
        reset_handlers: 是否重置之前的日志处理器(批量回测需要)
    
    Returns:
        str: 日志文件路径
    """
    log_dir = './logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 生成包含日期的日志文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if date_str:
        log_file = f'{log_dir}/backtest_{date_str}_{timestamp}.log'
    else:
        log_file = f'{log_dir}/backtest_{timestamp}.log'
    
    # 清除之前的日志处理器(批量回测时需要)
    if reset_handlers:
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            #logging.StreamHandler()
        ]
    )
    
    return log_file