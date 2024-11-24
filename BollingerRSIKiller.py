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
    timeframe = '5m'

    binance.cancel_all_orders(symbol)
    loss = -12
    target = 24
    gr.fecha_pnl(symbol, loss, target, timeframe)

    posicao_max = 0.002
    posicao = 0.002
    threshold = 0.0015

    #importar candles
    bars = binance.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=50)
    df_candles = pd.DataFrame(bars, columns=['time', 'abertura', 'max', 'min', 'fechamento', 'volume'])
    df_candles['time'] = pd.to_datetime(df_candles['time'], unit='ms', utc=True).map(lambda x: x.tz_convert('America/Sao_Paulo'))

    #cria metricas da estrategia
    rsi = RSIIndicator(df_candles['fechamento'])
    df_candles['RSI'] = rsi.rsi()

    #Bollinger Bands
    bollinger_bands = ta.bbands(df_candles.fechamento, length=30, std=2)
    bollinger_bands = bollinger_bands.iloc[:,[0,1,2]]
    bollinger_bands.columns = ['BBL', 'BBM', 'BBU']
    bollinger_bands['largura'] = ((bollinger_bands.BBU - bollinger_bands.BBL) / bollinger_bands.BBM)
    df_candles = pd.concat((df_candles, bollinger_bands), axis=1)

    print('****************************************')
    print(f"RSI: {df_candles.iloc[-2]['RSI']}")
    print(f"BBU: {df_candles.iloc[-2]['BBU']}")
    price = binance.fetch_trades(symbol)[-1]['price']
    price = float(binance.price_to_precision(symbol, price))
    print(f"PRICE: {price}")
    print(f"BBL: {df_candles.iloc[-2]['BBL']}")
    print('****************************************')
    #abrir long
    if df_candles.iloc[-1]['largura'] >= threshold and df_candles.iloc[-2]['RSI'] <= 35 and df_candles.iloc[-2]['fechamento'][-2] <= df_candles.iloc[-2]['BBL'] and price >= df_candles.iloc[-2]['max']:
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

    elif df_candles.iloc[-1]['largura'] >= threshold and df_candles.iloc[-2]['RSI'] >= 65 and df_candles.iloc[-2]['fechamento'][-2] >= df_candles.iloc[-2]['BBU'] and price <= df_candles.iloc[-2]['min']:       
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

schedule.every(25).seconds.do(job)

while True:
    try:
        schedule.run_pending()
    except:
        print('Problemas de conexão...')
        time.sleep(10)  