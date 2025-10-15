import json
from utils.config import address_list
from utils.average_holding_time import AverageHoldingTimeAnalyzer

address_list = json.loads(address_list)
trades = address_list.get("data", {}).get("trades", [])

high_frequency_traders = []

for trade in trades:
    address = trade.get("address")
    if address:
        analyzer = AverageHoldingTimeAnalyzer(address)
        address = analyzer.analyze()
        if address:
            high_frequency_traders.append(address)
    else:
        print(f"Address is empty for trade: {trade}")

print(high_frequency_traders)
