import config as k
import pandas as pd
import ccxt
import pandas_ta as ta
import time
from ta.momentum import RSIIndicator
import GerenciamentoRisco as gr
import schedule
import TelegramBot

def job():
    binance = ccxt.binance({'enableRateLimit':True,
                            'apiKey': k.binancekey,
                            'secret': k.binancesecret,
                            'options':{
                                'defaultType': 'future',
                            }
    })

    symbol = 'BTCUSDT'

    binance.cancel_all_orders(symbol)
    loss = -12
    target = 24
    gr.fecha_pnl(symbol, loss, target, timeframe)

    posicao_max = 0.002
    posicao = 0.002

    #importar candles
    timeframe = '15m'
    bars = binance.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=50)
    df_candles = pd.DataFrame(bars, columns=['time', 'abertura', 'max', 'min', 'fechamento', 'volume'])
    df_candles['time'] = pd.to_datetime(df_candles['time'], unit='ms', utc=True).map(lambda x: x.tz_convert('America/Sao_Paulo'))

    #cria metricas da estrategia
    rsi = RSIIndicator(df_candles['fechamento'])
    df_candles['RSI'] = rsi.rsi()

    df_candles['EMA_20'] = ta.ema(close=df_candles.fechamento, length=20)

    macd = df_candles.ta.macd(close='fechamento', fast=12, slow=26, signal=9, append=True)
    df_candles = pd.concat([df_candles, macd], axis=1)

    df_candles['preco_ponderado'] = df_candles['fechamento'] * df_candles['volume']
    df_candles['VWAP'] = df_candles['preco_ponderado'].sum() / df_candles['volume'].sum()

    print(f"RSI: {df_candles.iloc[-1]['RSI']}")
    print(f"EMA20: {df_candles.iloc[-1]['EMA_20']}")
    print(f"MACD: {df_candles.iloc[-1]['MACD_12_26_9']}")
    print(f"VWAP: {df_candles.iloc[-1]['VWAP']}")

    #condicoes long e short
    price = binance.fetch_trades(symbol)[-1]['price']
    price = float(binance.price_to_precision(symbol, price))

    #abrir long
    if df_candles.iloc[-1]['RSI'] <= 30 and price >= df_candles.iloc[-1]['EMA_20'] and price >= df_candles.iloc[-1]['VWAP']:
        if df_candles.iloc[-1]['MACD_12_26_9'] >= df_candles.iloc[-1]['MACDs_12_26_9']:
            if not gr.posicao_max(symbol, posicao_max) and gr.posicoes_abertas(symbol)[0] != 'short' and not gr.ultima_ordem_aberta(symbol):
                try:
                    bid, ask = gr.livro_ofertas(symbol)
                    bid = binance.price_to_precision(symbol, bid)
                    binance.create_order(symbol, side='buy', type='LIMIT', price=bid, amount=posicao, params= {'hedged':'true'})
                    print(f"****** ABRINDO LONG DE {posicao} MODAS EM {symbol}! ******")
                    msg = f'WeaponCandle: Abrindo LONG {posicao} {symbol}'
                    TelegramBot.enviar_msg(msg)
                except:
                    print("****** Problema ao abrir long! ******")

    elif df_candles.iloc[-1]['RSI'] >= 70 and price <= df_candles.iloc[-1]['EMA_20'] and price <= df_candles.iloc[-1]['VWAP']:
        if df_candles.iloc[-1]['MACD_12_26_9'] <= df_candles.iloc[-1]['MACDs_12_26_9']:
            if not gr.posicao_max(symbol, posicao_max) and gr.posicoes_abertas(symbol)[0] != 'long' and not gr.ultima_ordem_aberta(symbol):
                try:
                    bid, ask = gr.livro_ofertas(symbol)
                    ask = binance.price_to_precision(symbol, ask)
                    binance.create_order(symbol, side='sell', type='LIMIT', price=bid, amount=posicao, params= {'hedged':'true'})
                    print(f"****** ABRINDO SHORT DE {posicao} MODAS EM {symbol}! ******")
                    msg = f'WeaponCandle: Abrindo SHORT {posicao} {symbol}'
                    TelegramBot.enviar_msg(msg)
                except:
                    print("****** Problema ao abrir long! ******")

    else:
        print("***** Sem tendencia para long ou short... *****")

#aglutinar tudo e schedular! 

schedule.every(15).seconds.do(job)

while True:
    try:
        schedule.run_pending()
    except:
        print('Problemas de conexão...')
        time.sleep(10)  