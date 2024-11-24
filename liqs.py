import asyncio
import json 
import os 
from datetime import datetime 
import pytz 
from websockets import connect 
from termcolor import cprint 

websocket_url = 'wss://fstream.binance.com/ws/!forceOrder@arr'
filename = 'binance.csv'

if not os.path.isfile(filename):
    with open(filename, 'w') as f:
        f.write(",".join([
            'symbol', 'side', 'order_type', 'time_in_force',
            'original_quantity', 'price', 'average_price', 'order_status',
            'order_last_filled_quantity', 'order_filled_accumulated_quantity',
            'order_trade_time', 'usd_size'
        ])+ "\n") 

# {'s': 'BTCUSDT', 'S': 'BUY', 'o': 'LIMIT', 'f': 'IOC', 'q': '0.004', 'p': '65691.45', 'ap': '65440.50', 'X': 'FILLED', 'l': '0.004', 'z': '0.004', 'T': 1722550570171}

async def binance_liquidation(uri, filename):
    async with connect(uri) as websocket:
        while True:
            try:
                msg = await websocket.recv()
                order_data = json.loads(msg)['o']
                # print(order_data)
                symbol = order_data['s'].replace('USDT', '')
                side = order_data['S']
                timestamp = int(order_data['T'])
                filled_quantity = float(order_data['z'])
                price = float(order_data['p'])
                usd_size = filled_quantity * price
                est = pytz.timezone("America/Sao_Paulo")
                time_est = datetime.fromtimestamp(timestamp/ 1000, est).strftime('%H:%M:%S')
                if usd_size > 5000:
                    liquidation_type = 'LONG LIQ' if side == 'SELL' else 'SHORT LIQ'
                    symbol = symbol[:4]
                    output = f"{liquidation_type} {symbol} {time_est} {usd_size:,.0f}"
                    color = 'green' if side == 'SELL' else 'red'
                    attrs = ['bold'] if usd_size > 10000 else []

                    if usd_size > 250000:
                        stars = '*' * 3 
                        attrs.append('blink')
                        output = f'{stars}{output}'
                        for _ in range(4):
                            cprint(output, 'white', f'on_{color}', attrs=attrs)
                    elif usd_size > 100000:
                        starts = '*' *1
                        attrs.append('blink')
                        output = f'{stars}{output}'
                        for _ in range(2):
                            cprint(output, 'white', f'on_{color}', attrs=attrs)

                    elif usd_size > 25000:
                        cprint(output, 'white', f'on_{color}', attrs=attrs)

                    else:
                        cprint(output, 'white', f'on_{color}')

                    print('')

                    # if liquidation_type = 'L LIQ': ...
                        

                msg_values = [str(order_data.get(key)) for key in ['s', 'S', 'o', 'f', 'q', 'p', 'ap', 'X', 'l', 'z', 'T']]
                msg_values.append(str(usd_size))
                with open(filename, 'a') as f:
                    trade_info = ','.join(msg_values) + '\n'
                    trade_info = trade_info.replace('USDT', '')
                    f.write(trade_info)

            except Exception as e:
                await asyncio.sleep(5)

asyncio.run(binance_liquidation(websocket_url, filename))