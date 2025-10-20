# Filter High Frequency Traders from ApexLiquid

## 项目概述

这是一个用于分析和过滤 Hyperliquid 交易平台上高频交易者的 Python 工具。该项目通过分析用户的成交记录，计算平均持仓时间，识别可能的高频交易者，并提供黑名单功能以排除已知地址。

---

## 关联项目

参考与数据来源：`https://github.com/zhajingwen/calculate-average-hold-time-for-for-hyperliquid-user`

---

## 功能特性

### 核心功能
- **交易数据分析**: 从 Hyperliquid API 拉取指定用户的成交记录
- **持仓时间计算**: 使用 FIFO（先进先出）算法计算币种的平均/加权平均持仓时间
- **高频交易者识别**: 基于总体简单平均持仓时间阈值进行识别（当前阈值为 1 小时）
- **黑名单过滤**: 支持在 `utils/blacklist.txt` 里屏蔽已知地址
- **合约与现货**: 支持对合约与现货分开统计并输出综合对比

### 指标维度
- 简单平均、加权平均、最短/最长持仓时间
- 合约、现货、合并三种视角的总体统计

## 项目结构（当前）

```
filter-high-frequency-traders-from-from-apexliquid/
├── main.py                         # 批量过滤入口（读取黑名单与地址列表）
├── pyproject.toml                  # 项目与依赖声明（使用 uv/pip 安装）
├── README.md                       # 项目说明文档（本文件）
└── utils/
    ├── average_holding_time.py     # 持仓时间分析器
    ├── blacklist.txt               # 黑名单地址，一行一个
    └── config.py                   # 内置的地址列表（JSON 字符串）
```

与早期文档不同：项目当前没有 `utils/__init__.py` 与 `*.egg-info/` 目录。

## 安装与环境

### 环境要求
- Python >= 3.13（与 `pyproject.toml` 保持一致）
- requests >= 2.32.5

### 安装方式
本项目使用 `pyproject.toml` 管理依赖。可任选以下方式安装依赖：

```bash
# 方式 A：使用 uv（推荐）
uv sync

# 方式 B：使用 pip 直接安装依赖
pip install "requests>=2.32.5"
```

提示：当前仓库未提供 `requirements.txt`，请按上述方式安装依赖。

## 配置
1. 在 `utils/blacklist.txt` 中添加需要过滤的地址（每行一个）。
2. 在 `utils/config.py` 中维护 `address_list`（JSON 字符串），程序会从中读取 `data.trades[].address` 作为候选。

## 使用方法

### 运行
```bash
python main.py
```

程序逻辑概述：
1. 读取 `utils/config.py` 内置的地址列表与 `utils/blacklist.txt` 黑名单。
2. 对每个未在黑名单中的地址：
   - 调用 Hyperliquid `userFills` 接口拉取成交记录；
   - 计算合约/现货持仓时间统计；
   - 计算总体简单平均持仓时间，若 ≤ 1 小时则判定为“高频”，打印详情并返回该地址。
3. 最终打印识别出的高频地址列表。

### 分析器使用示例
```python
from utils.average_holding_time import AverageHoldingTimeAnalyzer

analyzer = AverageHoldingTimeAnalyzer("0x1234...")
address = analyzer.analyze()  # 若总体简单平均持仓时间 ≤ 1 小时，会打印报告并返回地址
```

## 核心类与主要方法

### `AverageHoldingTimeAnalyzer`
- `fetch_user_fills()`: 拉取用户成交记录
- `calculate_average_holding_time()`: 计算并拆分合约/现货的持仓时间
- `get_coin_statistics(coin, is_spot=False)`: 获取某币种统计
- `get_overall_statistics(is_spot=None)`: 获取总体统计（合约/现货/合并）
- `print_statistics()`: 打印完整统计（合约、现货、综合对比）
- `analyze()`: 执行完整流程并按阈值输出高频判定

数据成员：`perp_holding_times`、`spot_holding_times`、`perp_positions`、`spot_positions`。

### 计算与判定
- FIFO 拆解开/平仓，支持部分平仓；
- 以小时为单位计算持仓时长，支持按仓位大小进行加权；
- 当前“高频”阈值：总体简单平均持仓时间 ≤ 1 小时。

## API 说明（拉取成交记录）

- 端点：`https://api.hyperliquid.xyz/info`
- 方法：POST
- Body 示例：
```json
{
  "aggregateByTime": true,
  "type": "userFills",
  "user": "0x1234..."
}
```

备注：`utils/config.py` 中的示例 JSON 结构用于提供待分析的地址列表（来源于 Top Trades），与 `userFills` 返回结构不同，程序会分别处理。

## 输出示例

控制台报告将包含合约/现货各自的币种统计及总体统计，并在满足“高频”条件时输出详细报告与地址列表。例如：

```
正在获取用户 0x1234... 的交易记录...
成功获取 150 条交易记录
其中: 合约交易 120 条, 现货交易 30 条
...
['0x1234...', '0x5678...']
```

## 注意与已知限制
- API 频控：注意 Hyperliquid API 的速率限制；
- 数据完整性：持仓时间依赖成交明细，请确保数据完整；
- 黑名单维护：定期更新 `utils/blacklist.txt`；
- 现货识别规则：`_is_spot_trade` 方法标注“算法存在严重问题，待修正”，现阶段以 `dir in ['Buy','Sell']` 识别现货，可能在部分数据下不准确，后续将完善；
- Python 版本：与 `pyproject.toml` 要求一致（>=3.13）。

## 技术栈
- Python 3.13+
- requests
- 标准库：json / datetime / collections

## 贡献
1. Fork 仓库
2. 创建分支
3. 提交更改
4. 发起 Pull Request

## 许可证
请查看项目根目录中的许可证文件（若有）。

## 交流
欢迎通过 Issue / PR 反馈问题与建议。
