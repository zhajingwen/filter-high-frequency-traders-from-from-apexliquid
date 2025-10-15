import requests
from collections import defaultdict
from datetime import datetime, timedelta

def fetch_user_fills(user_address):
    """
    获取用户的成交记录
    """
    url = "https://api.hyperliquid.xyz/info"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    body = {
        "aggregateByTime": True,
        "type": "userFills",
        "user": user_address
    }
    
    response = requests.post(url, json=body, headers=headers)
    response.raise_for_status()
    return response.json()

def calculate_average_holding_time(fills):
    """
    计算每个币种的平均持仓时间
    
    逻辑：
    1. 追踪每个币种的持仓队列（FIFO）
    2. 开仓时记录开仓时间和数量
    3. 平仓时计算持仓时间
    """
    # 存储每个币种的持仓队列 {coin: [(open_time, size, price)]}
    positions = defaultdict(list)
    
    # 存储每个币种的持仓时间记录 {coin: [holding_times]}
    holding_times = defaultdict(list)
    
    # 按时间排序（从早到晚）
    fills_sorted = sorted(fills, key=lambda x: x['time'])
    
    for fill in fills_sorted:
        coin = fill['coin']
        size = float(fill['sz'])
        time = fill['time']  # 毫秒时间戳
        direction = fill['dir']
        
        # 判断是开仓还是平仓
        is_opening = 'Open' in direction
        
        if is_opening:
            # 开仓：记录开仓信息
            positions[coin].append({
                'time': time,
                'size': size,
                'price': float(fill['px'])
            })
        else:
            # 平仓：计算持仓时间（使用FIFO）
            remaining_size = size
            
            while remaining_size > 0 and positions[coin]:
                position = positions[coin][0]
                
                if position['size'] <= remaining_size:
                    # 完全平掉这个仓位
                    holding_time_ms = time - position['time']
                    holding_time_hours = holding_time_ms / (1000 * 60 * 60)
                    
                    holding_times[coin].append({
                        'holding_time_hours': holding_time_hours,
                        'size': position['size'],
                        'open_time': position['time'],
                        'close_time': time
                    })
                    
                    remaining_size -= position['size']
                    positions[coin].pop(0)
                else:
                    # 部分平仓
                    holding_time_ms = time - position['time']
                    holding_time_hours = holding_time_ms / (1000 * 60 * 60)
                    
                    holding_times[coin].append({
                        'holding_time_hours': holding_time_hours,
                        'size': remaining_size,
                        'open_time': position['time'],
                        'close_time': time
                    })
                    
                    position['size'] -= remaining_size
                    remaining_size = 0
    
    return holding_times, positions

def format_time(hours):
    """格式化时间显示"""
    if hours < 1:
        return f"{hours * 60:.1f} 分钟"
    elif hours < 24:
        return f"{hours:.1f} 小时"
    else:
        days = hours / 24
        return f"{days:.1f} 天"

def print_statistics(holding_times, positions):
    """打印统计信息"""
    print("=" * 80)
    print("持仓时间统计报告")
    print("=" * 80)
    
    if not holding_times:
        print("\n未找到已平仓的交易记录")
        return
    
    # 计算总体平均持仓时间
    all_holding_times = []
    all_weighted_times = []
    
    for coin, times in holding_times.items():
        print(f"\n【{coin}】")
        print("-" * 80)
        
        if not times:
            print("  无已平仓记录")
            continue
        
        # 简单平均（不考虑仓位大小）
        simple_avg = sum(t['holding_time_hours'] for t in times) / len(times)
        
        # 加权平均（考虑仓位大小）
        total_size = sum(t['size'] for t in times)
        weighted_avg = sum(t['holding_time_hours'] * t['size'] for t in times) / total_size
        
        # 最短和最长持仓时间
        min_time = min(t['holding_time_hours'] for t in times)
        max_time = max(t['holding_time_hours'] for t in times)
        
        print(f"  平仓次数: {len(times)}")
        print(f"  简单平均持仓时间: {format_time(simple_avg)}")
        print(f"  加权平均持仓时间: {format_time(weighted_avg)} (按仓位大小加权)")
        print(f"  最短持仓时间: {format_time(min_time)}")
        print(f"  最长持仓时间: {format_time(max_time)}")
        print(f"  总平仓量: {total_size:.4f}")
        
        # 收集用于总体统计
        all_holding_times.extend([t['holding_time_hours'] for t in times])
        all_weighted_times.extend([t['holding_time_hours'] * t['size'] for t in times])
    
    # 打印总体统计
    if all_holding_times:
        print("\n" + "=" * 80)
        print("【总体统计】")
        print("-" * 80)
        overall_simple_avg = sum(all_holding_times) / len(all_holding_times)
        overall_weighted_avg = sum(all_weighted_times) / sum(t['size'] for coin_times in holding_times.values() for t in coin_times)
        
        print(f"  总平仓次数: {len(all_holding_times)}")
        print(f"  总体简单平均持仓时间: {format_time(overall_simple_avg)}")
        print(f"  总体加权平均持仓时间: {format_time(overall_weighted_avg)}")
    
    # 打印未平仓位
    open_positions = {coin: pos for coin, pos in positions.items() if pos}
    if open_positions:
        print("\n" + "=" * 80)
        print("【当前未平仓位】")
        print("-" * 80)
        for coin, pos_list in open_positions.items():
            total_open = sum(p['size'] for p in pos_list)
            print(f"  {coin}: {total_open:.4f} (共 {len(pos_list)} 个开仓记录)")

def main():
    # 用户地址
    # user_address = "0x5c9c9ab381c841530464ef9ee402568f84c3b676"
    user_address = "0xf709deb9ca069e53a31a408fde397a87d025a352"
    
    print(f"正在获取用户 {user_address} 的交易记录...\n")
    
    try:
        # 获取数据
        fills = fetch_user_fills(user_address)
        
        if not fills:
            print("未找到交易记录")
            return
        
        print(f"成功获取 {len(fills)} 条交易记录\n")
        
        # 计算持仓时间
        holding_times, positions = calculate_average_holding_time(fills)
        
        # 打印统计信息
        print_statistics(holding_times, positions)
        
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()