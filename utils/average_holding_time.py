import requests
from collections import defaultdict
from datetime import datetime, timedelta


class AverageHoldingTimeAnalyzer:
    """Hyperliquid交易数据分析器"""
    
    def __init__(self, user_address):
        """
        初始化分析器
        
        Args:
            user_address: 用户地址
        """
        self.user_address = user_address
        self.api_url = "https://api.hyperliquid.xyz/info"
        self.fills = []
        self.holding_times = defaultdict(list)
        self.positions = defaultdict(list)
    
    def fetch_user_fills(self):
        """获取用户的成交记录"""
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        body = {
            "aggregateByTime": True,
            "type": "userFills",
            "user": self.user_address
        }
        
        response = requests.post(self.api_url, json=body, headers=headers)
        response.raise_for_status()
        self.fills = response.json()
        return self.fills
    
    def calculate_average_holding_time(self):
        """
        计算每个币种的平均持仓时间
        
        逻辑：
        1. 追踪每个币种的持仓队列（FIFO）
        2. 开仓时记录开仓时间和数量
        3. 平仓时计算持仓时间
        """
        # 重置数据
        self.positions = defaultdict(list)
        self.holding_times = defaultdict(list)
        
        # 按时间排序（从早到晚）
        fills_sorted = sorted(self.fills, key=lambda x: x['time'])
        
        for fill in fills_sorted:
            coin = fill['coin']
            size = float(fill['sz'])
            time = fill['time']  # 毫秒时间戳
            direction = fill['dir']
            
            # 判断是开仓还是平仓
            is_opening = 'Open' in direction
            
            if is_opening:
                self._handle_opening(coin, size, time, float(fill['px']))
            else:
                self._handle_closing(coin, size, time)
        
        return self.holding_times, self.positions
    
    def _handle_opening(self, coin, size, time, price):
        """处理开仓"""
        self.positions[coin].append({
            'time': time,
            'size': size,
            'price': price
        })
    
    def _handle_closing(self, coin, size, time):
        """处理平仓（FIFO）"""
        remaining_size = size
        
        while remaining_size > 0 and self.positions[coin]:
            position = self.positions[coin][0]
            
            if position['size'] <= remaining_size:
                # 完全平掉这个仓位
                holding_time_ms = time - position['time']
                holding_time_hours = holding_time_ms / (1000 * 60 * 60)
                
                self.holding_times[coin].append({
                    'holding_time_hours': holding_time_hours,
                    'size': position['size'],
                    'open_time': position['time'],
                    'close_time': time
                })
                
                remaining_size -= position['size']
                self.positions[coin].pop(0)
            else:
                # 部分平仓
                holding_time_ms = time - position['time']
                holding_time_hours = holding_time_ms / (1000 * 60 * 60)
                
                self.holding_times[coin].append({
                    'holding_time_hours': holding_time_hours,
                    'size': remaining_size,
                    'open_time': position['time'],
                    'close_time': time
                })
                
                position['size'] -= remaining_size
                remaining_size = 0
    
    @staticmethod
    def format_time(hours):
        """格式化时间显示"""
        if hours < 1:
            return f"{hours * 60:.1f} 分钟"
        elif hours < 24:
            return f"{hours:.1f} 小时"
        else:
            days = hours / 24
            return f"{days:.1f} 天"
    
    def get_coin_statistics(self, coin):
        """
        获取指定币种的统计数据
        
        Returns:
            dict: 包含各项统计指标的字典
        """
        times = self.holding_times.get(coin, [])
        
        if not times:
            return None
        
        simple_avg = sum(t['holding_time_hours'] for t in times) / len(times)
        total_size = sum(t['size'] for t in times)
        weighted_avg = sum(t['holding_time_hours'] * t['size'] for t in times) / total_size
        min_time = min(t['holding_time_hours'] for t in times)
        max_time = max(t['holding_time_hours'] for t in times)
        
        return {
            'coin': coin,
            'close_count': len(times),
            'simple_avg': simple_avg,
            'weighted_avg': weighted_avg,
            'min_time': min_time,
            'max_time': max_time,
            'total_size': total_size
        }
    
    def get_overall_statistics(self):
        """获取总体统计数据"""
        all_holding_times = []
        all_weighted_times = []
        
        for coin, times in self.holding_times.items():
            all_holding_times.extend([t['holding_time_hours'] for t in times])
            all_weighted_times.extend([t['holding_time_hours'] * t['size'] for t in times])
        
        if not all_holding_times:
            return None
        
        total_size = sum(t['size'] for coin_times in self.holding_times.values() for t in coin_times)
        
        return {
            'total_close_count': len(all_holding_times),
            'overall_simple_avg': sum(all_holding_times) / len(all_holding_times),
            'overall_weighted_avg': sum(all_weighted_times) / total_size
        }
    
    def get_open_positions(self):
        """获取未平仓位"""
        return {coin: pos for coin, pos in self.positions.items() if pos}
    
    def print_statistics(self, overall):
        """打印统计信息"""
        print("=" * 80)
        print("持仓时间统计报告")
        print("=" * 80)
        
        if not self.holding_times:
            print("\n未找到已平仓的交易记录")
            return
        
        # 打印每个币种的统计
        for coin in self.holding_times.keys():
            stats = self.get_coin_statistics(coin)
            
            if stats is None:
                continue
            
            print(f"\n【{coin}】")
            print("-" * 80)
            print(f"  平仓次数: {stats['close_count']}")
            print(f"  简单平均持仓时间: {self.format_time(stats['simple_avg'])}")
            print(f"  加权平均持仓时间: {self.format_time(stats['weighted_avg'])} (按仓位大小加权)")
            print(f"  最短持仓时间: {self.format_time(stats['min_time'])}")
            print(f"  最长持仓时间: {self.format_time(stats['max_time'])}")
            print(f"  总平仓量: {stats['total_size']:.4f}")
        
        # 打印总体统计
        if overall:
            print("\n" + "=" * 80)
            print("【总体统计】")
            print("-" * 80)
            print(f"  总平仓次数: {overall['total_close_count']}")
            print(f"  总体简单平均持仓时间: {self.format_time(overall['overall_simple_avg'])}")
            print(f"  总体加权平均持仓时间: {self.format_time(overall['overall_weighted_avg'])}")
        
        # 打印未平仓位
        open_positions = self.get_open_positions()
        if open_positions:
            print("\n" + "=" * 80)
            print("【当前未平仓位】")
            print("-" * 80)
            for coin, pos_list in open_positions.items():
                total_open = sum(p['size'] for p in pos_list)
                print(f"  {coin}: {total_open:.4f} (共 {len(pos_list)} 个开仓记录)")
    
    def analyze(self):
        """执行完整的分析流程"""
        print(f"正在获取用户 {self.user_address} 的交易记录...\n")
        
        try:
            # 获取数据
            fills = self.fetch_user_fills()
            
            if not fills:
                print("未找到交易记录")
                return
            
            print(f"成功获取 {len(fills)} 条交易记录\n")
            
            # 计算持仓时间
            self.calculate_average_holding_time()
            # 获取总体统计数据
            overall = self.get_overall_statistics()
            overall_simple_avg = overall['overall_simple_avg']
            if overall_simple_avg > 1:
                print(f"总体简单平均持仓时间: {overall_simple_avg} 小时 {self.user_address}")
                return
            # 打印统计信息
            self.print_statistics(overall)
            return self.user_address
            
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
        except Exception as e:
            print(f"发生错误: {e}")
            import traceback
            traceback.print_exc()


def main():
    # 用户地址
    # user_address = "0x5c9c9ab381c841530464ef9ee402568f84c3b676"
    user_address = "0xf709deb9ca069e53a31a408fde397a87d025a352"
    
    # 创建分析器并执行分析
    analyzer = AverageHoldingTimeAnalyzer(user_address)
    analyzer.analyze()


if __name__ == "__main__":
    main()