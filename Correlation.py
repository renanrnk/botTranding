import config as k
import pandas as pd
import ccxt
import pandas_ta as ta
import time
from ta.momentum import RSIIndicator
import GerenciamentoRisco as gr
import schedule
import TelegramBot

def calc_sup_rest(df, tamanho=50):
    df['suporte'] = df['min'].rolling(window=tamanho).min()
    df['resistencia'] = df['max'].rolling(window=tamanho).max()

    return df.iloc[-2]['suporte'], df.iloc[-2]['resistencia']

def job():
    binance = ccxt.binance({'enableRateLimit':True,
                            'apiKey': k.binancekey,
                            'secret': k.binancesecret,
                            'options':{
                                'defaultType': 'future',
                            }
    })

    symbol = 'ETHUSDT'
    timeframe = '15m'
    bars = binance.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=50)
    df_candles = pd.DataFrame(bars, columns=['time', 'abertura', 'max', 'min', 'fechamento', 'volume'])
    df_candles['time'] = pd.to_datetime(df_candles['time'], unit='ms', utc=True).map(lambda x: x.tz_convert('America/Sao_Paulo'))

    #definir stop loss e gain
    stop_loss = 0.01
    take_profit = 0.04

    #moedas para operar e possicao MAXIMA!
    alt_coins = {'LINK/USDT': 20, 'CHZ/USDT':3000, '1000SHIB/USDT':1500, 'TIA/USDT':50}

    #Aplicar funcao sup e resistencia
    suporte, resistencia = calc_sup_rest(df_candles)

    #preço do eth
    price = binance.fetch_trades(symbol)[-1]['price']

    if price > resistencia:
        
        coinData = {}

        for coin in alt_coins:
            altcoins_price = binance.fetch_trades(coin)[-1]['price']
            coinData[coin] = abs((altcoins_price - price) / price) * 100

        most_lagging = min(coinData, key=coinData.get)
        pos = alt_coins[most_lagging]

        if not gr.posicao_max(most_lagging, pos):
            # preco da operacao
            altcoins_price = binance.fetch_trades(symbol)[-1]['price']
            altcoin_price = float(binance.price_to_precision(most_lagging, altcoin_price))

            #preco do stop
            altcoins_price_stop_loss = altcoins_price * (1-stop_loss)
            altcoins_price_stop_loss = float(binance.price_to_precision(most_lagging, altcoins_price_stop_loss))

            #preco taket profit
            altcoins_price_take_profit = altcoins_price * (1+stop_loss)
            altcoins_price_take_profit = float(binance.price_to_precision(most_lagging, altcoins_price_take_profit))

            binance.cancell_all_orders(most_lagging)
            binance.create_order(symbol=most_lagging, side='buy', type='MARKET', amount=pos, params={'hedged':'true'})
            binance.create_order(symbol=most_lagging, side='sell', type='STOP_MARKET', amount=pos, params={'stopPrice': altcoins_price_stop_loss})
            binance.create_order(symbol=most_lagging, side='sell', type='TAKE_PROFIT_MARKET', amount=pos, params={'stopPrice': altcoins_price_take_profit})


    elif price < suporte:

        coinData = {}
        for coin in alt_coins:
            altcoins_price = binance.fetch_trades(coin)[-1]['price']
            coinData[coin] = abs((altcoins_price - price) / price) * 100

        most_lagging = min(coinData, key=coinData.get)
        pos = alt_coins[most_lagging]

        if not gr.posicao_max(most_lagging, pos):
            altcoins_price = binance.fetch_trades(symbol)[-1]['price']
            altcoin_price = float(binance.price_to_precision(most_lagging, altcoin_price))

            #preco do stop
            altcoins_price_stop_loss = altcoins_price * (1+stop_loss)
            altcoins_price_stop_loss = float(binance.price_to_precision(most_lagging, altcoins_price_stop_loss))

            #preco taket profit
            altcoins_price_take_profit = altcoins_price * (1-stop_loss)
            altcoins_price_take_profit = float(binance.price_to_precision(most_lagging, altcoins_price_take_profit))

            binance.cancell_all_orders(most_lagging)
            binance.create_order(symbol=most_lagging, side='sell', type='MARKET', amount=pos, params={'hedged':'true'})
            binance.create_order(symbol=most_lagging, side='buy', type='STOP_MARKET', amount=pos, params={'stopPrice': altcoins_price_stop_loss})
            binance.create_order(symbol=most_lagging, side='buy', type='TAKE_PROFIT_MARKET', amount=pos, params={'stopPrice': altcoins_price_take_profit})
                 
    else:
        print('**** ETH NÃO ROMPEU! ****')



schedule.every(25).seconds.do(job)

while True:
    try:
        schedule.run_pending()
    except:
        print('Problemas de conexão...')
        time.sleep(10)  
