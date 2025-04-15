import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import seaborn as sns
from matplotlib.font_manager import FontProperties


file_path = r"D:\Users\tianhao\data\ABC实习\mystrategy\trades\arb_trades_USDT_thresh0.10_20250415_134450.xlsx"

# 检查文件是否存在
if not os.path.exists(file_path):
    print(f"错误：文件 {file_path} 不存在！")
    exit(1)

# 读取Excel文件
try:
    df = pd.read_excel(file_path)
    print(f"成功读取文件，共 {len(df)} 条交易记录")
except Exception as e:
    print(f"读取文件时出错：{str(e)}")
    exit(1)

# 检查profit_rate列是否存在
if 'profit_rate' not in df.columns:
    print("错误：Excel文件中没有找到'profit_rate'列！")
    exit(1)

# 基本统计分析
profit_rate = df['profit_rate']

print("\n===== 收益率基本统计 =====")
print(f"记录数量：{len(profit_rate)}")
print(f"最小值：{profit_rate.min():.4f}%")
print(f"最大值：{profit_rate.max():.4f}%")
print(f"平均值：{profit_rate.mean():.4f}%")
print(f"中位数：{profit_rate.median():.4f}%")
print(f"标准差：{profit_rate.std():.4f}%")
print(f"总和：{profit_rate.sum():.4f}%")

# 分位数统计
print("\n===== 分位数统计 =====")
quantiles = [0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
quantile_values = np.percentile(profit_rate, [q * 100 for q in quantiles])
for q, val in zip(quantiles, quantile_values):
    print(f"{q*100:3.0f}% 分位数: {val:.4f}%")

# 区间统计
print("\n===== 收益率区间分布 =====")
# 自动创建区间
min_val = profit_rate.min()
max_val = profit_rate.max()

# 根据数据范围自动创建区间
if max_val - min_val > 1:  # 如果范围大于1%，使用0.1%的间隔
    bins = np.arange(min_val // 0.1 * 0.1, max_val + 0.11, 0.1)
else:  # 否则使用0.05%的间隔
    bins = np.arange(min_val // 0.05 * 0.05, max_val + 0.051, 0.05)

# 统计每个区间的频数
hist, bin_edges = np.histogram(profit_rate, bins=bins)

print(f"区间大小: {bin_edges[1] - bin_edges[0]:.4f}%")
print("区间\t\t频数\t百分比")
for i in range(len(hist)):
    left_edge = bin_edges[i]
    right_edge = bin_edges[i+1]
    percentage = hist[i] / len(profit_rate) * 100
    print(f"{left_edge:.4f}% - {right_edge:.4f}%\t{hist[i]}\t{percentage:.2f}%")

# 可视化分析

# 设置中文显示
try:
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决保存图像是负号'-'显示为方块的问题
except:
    print("警告：无法设置中文显示，图表中文可能显示为方块")

# 创建图表 - 只有两个子图，使用1x2布局
plt.figure(figsize=(16, 6))

# 1. 直方图和密度图
plt.subplot(1, 2, 1)
sns.histplot(profit_rate, kde=True, color='royalblue')
plt.title('收益率分布直方图和密度曲线', fontsize=14)
plt.xlabel('收益率 (%)', fontsize=12)
plt.ylabel('频数', fontsize=12)
plt.grid(True, alpha=0.3)

# 2. 箱线图
plt.subplot(1, 2, 2)
sns.boxplot(y=profit_rate, color='royalblue')
plt.title('收益率箱线图', fontsize=14)
plt.ylabel('收益率 (%)', fontsize=12)
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('profit_rate_analysis.png', dpi=300)
plt.show()

print(f"\n分析图已保存至 profit_rate_analysis.png")

# 附加分析：统计正负收益率比例
positive_count = (profit_rate > 0).sum()
negative_count = (profit_rate <= 0).sum()
positive_percentage = positive_count / len(profit_rate) * 100
negative_percentage = negative_count / len(profit_rate) * 100

print("\n===== 正负收益率统计 =====")
print(f"正收益交易：{positive_count} 笔 ({positive_percentage:.2f}%)")
print(f"负收益交易：{negative_count} 笔 ({negative_percentage:.2f}%)")

# 正负收益率的平均值
if positive_count > 0:
    positive_mean = profit_rate[profit_rate > 0].mean()
    print(f"正收益平均值：{positive_mean:.4f}%")

if negative_count > 0:
    negative_mean = profit_rate[profit_rate <= 0].mean()
    print(f"负收益平均值：{negative_mean:.4f}%")

# 收益率排名前5和后5的交易
if len(profit_rate) >= 5:
    print("\n===== 收益率最高的5笔交易 =====")
    top5 = df.nlargest(5, 'profit_rate')
    print(top5[['datetime', 'profit_rate', 'path']].to_string(index=False))
    
    print("\n===== 收益率最低的5笔交易 =====")
    bottom5 = df.nsmallest(5, 'profit_rate')
    print(bottom5[['datetime', 'profit_rate', 'path']].to_string(index=False))