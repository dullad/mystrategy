import os
import json
import logging
from dataclasses import dataclass, field, asdict

@dataclass
class ArbConfig:
    """三角套利配置类，集中管理所有可配置参数"""
    # 基础配置
    base_currency: str = 'USDT'          # 基础货币
    initial_cash: float = 1000            # 初始资金
    threshold: float = 0.001             # 套利阈值
    
    # 数据配置
    interval: str = '1s'                # 数据时间间隔
    start_date: str = '2025-04-07'      # 起始日期
    end_date: str = '2025-04-07'        # 结束日期
    # 批量回测配置
    batch_test_dates: list = field(default_factory=lambda: [
        # 低迷行情
        ("2024-08-05", "2024-08-05"),  # 240805
        ("2024-09-06", "2024-09-06"),  # 240906
        ("2024-10-06", "2024-10-06"),  # 241006
        ("2024-12-30", "2024-12-30"),  # 241230
        
        # 高涨行情
        ("2024-07-13", "2024-07-13"),  # 240713
        ("2024-11-17", "2024-11-17"),  # 241117
        ("2024-12-18", "2024-12-18"),  # 241218
        ("2024-01-20", "2024-01-20"),  # 240120
        
        # 震荡行情
        ("2024-11-25", "2024-11-25"),  # 241125
        ("2024-12-28", "2024-12-28"),  # 241228
        ("2025-01-12", "2025-01-12"),  # 250112
        ("2025-03-18", "2025-03-18"),  # 250318
    ])

    data_dir: str = './data_binance'    # 数据目录
    download_data: bool = True          # 是否下载数据
    specific_data_dir: str = './data_binance/1s_20250407_20250407'    # 指定的数据目录路径
    # selected_pairs: list = field(default_factory=lambda: ["BTC_USDT", "ETH_BTC", "ETH_USDT", 
    #                                                       "SOL_BTC", "SOL_USDT", "BNB_ETH", 
    #                                                       "BNB_USDT", "XRP_BTC", "XRP_USDT", 
    #                                                       "LINK_ETH", "LINK_USDT", "DOGE_BTC", 
    #                                                       "DOGE_USDT", "DOT_BTC", "DOT_USDT", 
    #                                                       "USDC_USDT", "BTC_USDC", "ADA_BNB", 
    #                                                       "ADA_USDT","AVAX_BTC", "AVAX_USDT"]) # 选定的交易对列表
    selected_pairs: list = field(default_factory=lambda: ["ETH_BTC", "VELODROME_USDT", "LISTA_FDUSD", "FLOKI_TRY", "MBOX_TRY", "COOKIE_USDC", "DOGE_USDT", "RARE_USDC", "ANIME_USDC", "CHZ_TRY", "W_USDT", "ANKR_TRY", "KAITO_USDT", "ACA_USDT", "XLM_BTC", "PNUT_BTC", "PHA_USDT", "ATOM_USDC", "FLM_USDT", "ENJ_USDT", "GRT_TRY", "LEVER_TRY", "ACH_BTC", "S_USDT", "AIXBT_TRY", "EUR_USDC", "ADX_BTC", "COS_USDT", "PYTH_FDUSD", "WIN_EUR", "ZIL_ETH", "ANIME_USDT", "W_TRY", "BANANAS31_USDT", "XRP_BTC", "TUT_USDC", "XLM_FDUSD", "SOLV_BNB", "FLOKI_FDUSD", "LAYER_USDT", "HBAR_TRY", "TROY_TRY", "COOKIE_USDT", "GRT_EUR", "ALGO_BTC", "TRX_USDT", "DOGS_FDUSD", "RAY_USDC", "ENA_BTC", "SPELL_TRY", "GPS_USDC", "SAGA_USDT", "HMSTR_TRY", "VELODROME_USDC", "AUDIO_USDT", "PEPE_USDC", "XRP_USDT", "GALA_BRL", "ANIME_FDUSD", "S_FDUSD", "BONK_USDC", "1MBABYDOGE_TRY", "AEVO_TRY", "STX_USDC", "BB_TRY", "AUDIO_TRY", "VET_BNB", "CRV_TRY", "ADX_ETH", "DENT_TRY", "ALT_USDT", "ACA_BTC", "1000CAT_TRY", "XRP_EUR", "FDUSD_USDC", "GALA_TRY", "XTZ_USDT", "HMSTR_USDC", "1MBABYDOGE_USDT", "WIF_USDT", "BEAMX_USDT", "FET_TRY", "DOGE_EUR", "ARPA_TRY", "ROSE_USDT", "GRT_ETH", "HMSTR_FDUSD", "COTI_USDT", "SEI_FDUSD", "ONE_BTC", "BIO_USDT", "XLM_USDC", "SOL_FDUSD", "SHELL_TRY", "SOL_USDT", "BICO_BTC", "MINA_USDT", "POL_FDUSD", "SKL_BTC", "JUP_FDUSD", "CETUS_TRY", "PEOPLE_TRY", "RSR_USDT", "PEOPLE_FDUSD", "BSW_USDT", "T_USDC", "SAGA_USDC", "SUSHI_USDT", "POL_EUR", "VET_TRY", "ARK_TRY", "EOS_USDC", "TUT_USDT", "BROCCOLI714_USDT", "LISTA_USDT", "ETHFI_TRY", "SXP_BTC", "TURBO_USDT", "ALT_TRY", "ZK_USDC", "SC_ETH", "USTC_USDT", "NIL_USDT", "TRX_ETH", "ALT_FDUSD", "DOGE_USDC", "ANKR_USDT", "STX_BTC", "VANRY_TRY", "ARK_USDT", "MBOX_USDT", "POL_USDT", "SNT_USDT", "RUNE_USDT", "GPS_TRY", "ADA_BTC", "XLM_TRY", "DOGE_TRY", "PEOPLE_USDC", "ARB_USDT", "BOME_EUR", "GMT_USDT", "JUP_USDC", "WLD_BTC", "CRV_BTC", "ETH_USDC", "MEME_USDC", "SEI_USDC", "FLM_BTC", "TST_USDC", "RSR_USDC", "XAI_USDT", "POL_ETH", "GALA_FDUSD", "1000CHEEMS_USDC", "DOGS_USDC", "HOT_TRY", "GALA_USDT", "NOT_TRY", "PEPE_USDT", "VANRY_USDT", "WIF_FDUSD", "TRU_TRY", "MOVE_USDT", "REZ_USDC", "EURI_USDT", "XVG_USDT", "EDU_TRY", "VTHO_USDT", "1MBABYDOGE_USDC", "USUAL_USDT", "GUN_TRY", "NEXO_BTC", "LDO_USDC", "CETUS_USDC", "USUAL_TRY", "NEAR_USDC", "ZK_FDUSD", "SKL_USDT", "ONE_USDT", "FET_BTC", "WIF_USDC", "KAITO_USDC", "BOME_FDUSD", "SHIB_USDC", "SEI_BTC", "SLP_TRY", "WLD_USDT", "OP_USDC", "EOS_USDT", "OSMO_USDT", "VET_BTC", "BMT_TRY", "SAND_FDUSD", "BONK_TRY", "S_TRY", "PENGU_FDUSD", "LAYER_USDC", "BTC_FDUSD", "AMP_USDT", "PNUT_USDC", "NOT_USDT", "ZK_TRY", "FIL_USDC", "ACT_USDC", "EUR_EURI", "NEIRO_TRY", "VIDT_BTC", "USUAL_USDC", "1000SATS_TRY", "BTC_USDT", "STX_USDT", "FLOKI_USDT", "WIF_BTC", "CVC_USDC", "S_USDC", "SHELL_USDC", "SAND_BTC", "ZK_USDT", "LUNC_TRY", "STRAX_TRY", "COTI_BTC", "MINA_TRY", "RSR_TRY", "ROSE_BTC", "EOS_BTC", "LINK_FDUSD", "ZIL_USDT", "MEME_TRY", "CVC_USDT", "BAKE_TRY", "ENJ_BTC", "YGG_USDC", "TURBO_USDC", "FIDA_TRY", "FIDA_USDT", "ARDR_BTC", "XTZ_BTC", "CGPT_USDT", "ALT_USDC", "VET_USDT", "GMT_TRY", "ARPA_BTC", "PENGU_TRY", "ENA_USDT", "SXP_USDT", "IOTA_USDT", "MUBARAK_USDT", "PENGU_USDT", "WIN_USDT", "SEI_USDT", "DENT_ETH", "BONK_BRL", "BOME_TRY", "DOGE_BTC", "SAND_USDT", "BB_USDT", "TROY_USDT", "TRUMP_USDT", "XRP_TRY", "ZIL_BTC", "MEME_FDUSD", "LUNA_TRY", "BAKE_USDT", "NOT_USDC", "PARTI_USDT", "ACH_USDT", "CKB_USDC", "BONK_FDUSD", "FLOKI_USDC", "BOME_USDC", "KAIA_USDC", "OSMO_USDC", "GUN_BNB", "MEME_USDT", "DOGE_BRL", "SPELL_USDT", "XLM_USDT", "VANRY_USDC", "POL_TRY", "GUN_USDC", "BIO_TRY", "BB_BNB", "PIXEL_TRY", "DOGE_FDUSD", "FIL_USDT", "ENA_TRY", "G_TRY", "CRV_USDT", "PORTAL_USDT", "TRX_EUR", "OP_USDT", "CHZ_USDT", "AIXBT_USDC", "ALGO_USDT", "SHIB_DOGE", "TRU_USDT", "STX_FDUSD", "NIL_USDC", "GRT_USDT", "ELF_USDT", "SUSHI_BTC", "MANTA_TRY", "NEAR_USDT", "STRAX_BTC", "GRT_BTC", "PEPE_EUR", "ADA_TRY", "SHIB_BRL", "YGG_USDT", "1000SATS_USDC", "CGPT_USDC", "1000CAT_USDC", "ACT_TRY", "ENJ_TRY", "GALA_ETH", "NOT_FDUSD", "RUNE_USDC", "PNUT_TRY", "GPS_BNB", "CFX_USDT", "NFP_USDT", "LEVER_USDT", "GUN_FDUSD", "XEC_USDT", "EUR_USDT", "EDU_USDT", "1MBABYDOGE_FDUSD", "ELF_BTC", "XVG_TRY", "USTC_TRY", "STRAX_USDT", "WIN_TRX", "SHIB_FDUSD", "PYTH_USDC", "WIF_TRY", "MANTA_USDC", "XLM_ETH", "TLM_FDUSD", "ARPA_USDT", "ACA_TRY", "ADA_FDUSD", "PARTI_USDC", "HBAR_FDUSD", "RARE_TRY", "T_USDT", "XRP_USDC", "HBAR_BNB", "FDUSD_TRY", "LUNA_USDT", "PYTH_USDT", "ONE_TRY", "XAI_TRY", "ACT_USDT", "1000CAT_USDT", "CATI_USDT", "PIXEL_USDC", "BMT_USDT", "FDUSD_USDT", "CHZ_USDC", "SUI_USDC", "NEIRO_FDUSD", "SAND_USDC", "PEPE_BRL", "HBAR_BTC", "HIGH_USDT", "PHA_USDC", "TURBO_TRY", "WOO_BTC", "LUNC_USDT", "AMP_TRY", "NEXO_USDT", "VET_EUR", "GMT_EUR", "ETH_FDUSD", "PEPE_TRY", "CKB_USDT", "USDC_TRY", "ANIME_TRY", "MAV_USDT", "DOT_USDT", "COTI_TRY", "DYM_TRY", "XRP_FDUSD", "ENA_FDUSD", "CHZ_BTC", "SHIB_USDT", "WLD_USDC", "CRV_USDC", "BMT_USDC", "SHELL_USDT", "COS_TRY", "DOGS_USDT", "SOLV_TRY", "USDC_USDT", "SCR_USDT", "WOO_USDT", "PENGU_USDC", "TST_TRY", "CKB_TRY", "CFX_USDC", "JUP_USDT", "ARB_FDUSD", "PORTAL_FDUSD", "TST_USDT", "VIDT_USDT", "SUI_BTC", "BB_USDC", "TLM_TRY", "PEPE_FDUSD", "PEOPLE_USDT", "BERA_USDC", "REZ_USDT", "ACH_TRY", "BONK_USDT", "GUN_USDT", "BTTC_TRY", "BSW_TRY", "BICO_USDT", "TRX_USDC", "TRX_BTC", "HMSTR_USDT", "AEVO_USDT", "JUP_TRY", "BB_FDUSD", "TLM_USDC", "TLM_USDT", "OXT_USDT", "ARDR_USDT", "IOTA_BTC", "LDO_USDT", "RAY_USDT", "BERA_USDT", "ATOM_USDT", "USDT_BRL", "BNB_USDT", "DOGS_TRY", "STRK_USDT", "KAIA_USDT", "ROSE_TRY", "TROY_USDC", "SNT_ETH", "NEIRO_USDT", "ARB_USDC", "STRK_USDC", "ADA_USDT", "BEAMX_USDC", "SOLV_USDT", "GPS_USDT", "TRX_TRY", "1000CHEEMS_USDT", "ETHFI_USDT", "LINK_USDT", "TRX_XRP", "NEIRO_USDC", "BTTC_USDT", "DOT_USDC", "1000SATS_USDT", "MANA_USDT", "LRC_USDT", "ADX_USDT", "SC_USDT", "HIGH_TRY", "BROCCOLI714_USDC", "S_BTC", "CFX_BTC", "ETHFI_USDC", "ENA_USDC", "FET_USDT", "DYM_USDT", "POL_USDC", "VTHO_TRY", "PARTI_TRY", "ARB_BTC", "ETH_USDT", "LRC_TRY", "DENT_USDT", "SKL_TRY", "ADA_EUR", "XRP_ETH", "SOLV_FDUSD", "TRUMP_USDC", "MOVE_TRY", "G_USDT", "XEC_TRY", "NFP_TRY", "JASMY_TRY", "HOT_USDT", "JASMY_USDT", "ADA_ETH", "AIXBT_USDT", "MUBARAK_USDC", "SUI_USDT", "OGN_USDT", "OGN_BTC", "PIXEL_USDT", "SLP_USDT", "NIL_TRY", "CATI_TRY", "SHIB_TRY", "USDT_TRY", "PNUT_USDT", "IOTA_USDC", "MANA_BTC", "ADA_USDC", "ALGO_USDC", "BANANAS31_USDC", "SOL_USDC", "MANTA_USDT", "MAV_TRY", "XLM_EUR", "1000SATS_FDUSD", "OXT_BTC", "HBAR_USDC", "CETUS_USDT", "SCR_FDUSD", "SHIB_EUR", "FET_USDC", "RARE_USDT", "GALA_USDC", "REZ_TRY", "BEAMX_TRY", "BOME_USDT", "HBAR_USDT"]) # 选定的交易对列表

    # 流动性分析配置
    liquidity_volume_weight: float = 0.7    # 成交量权重
    liquidity_trades_weight: float = 0.3    # 交易次数权重
    liquidity_top_percent: float = 0.5      # 选取流动性最好的前50%交易对
    liquidity_min_pairs: int = 3            # 至少保留的交易对数量

    # 策略配置
    trade_amount: float = 100           # 每次交易金额
    max_positions: int = 5              # 最大持仓数
    skip_seconds: int = 3               # 执行交易后跳过的秒数
    commission_maker: float = 0.0005    # 挂单手续费率
    commission_taker: float = 0.0005    # 吃单手续费率
    
    # 其他配置
    debug: bool = False                 # 调试模式
    plot: bool = False                  # 是否生成图表
    
    def to_dict(self):
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建配置对象"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})
    
    @classmethod
    def from_file(cls, file_path):
        """从JSON文件加载配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            logging.error(f"加载配置文件 {file_path} 失败: {str(e)}")
            return cls()
    
    def save_to_file(self, file_path):
        """保存配置到JSON文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4)
        logging.info(f"配置已保存到: {file_path}")