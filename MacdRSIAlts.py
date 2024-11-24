# importar bibliotecas
import config as k
import pandas as pd
import ccxt 
import pandas_ta as ta
import time
from ta.momentum import RSIIndicator
import GerenciamentoRisco as gr
import schedule
import TelegramBot
from datetime import datetime
import pytz

# conexão
def run_bot():
    def job():

        binance = ccxt.binance({'enableRateLimit':True,
                            'apiKey': k.binancekey,
                            'secret': k.binancesecret,
                            'options': {
                                    'defaultType': 'future',
                                },
        })

        # confirmação de tendência com o BTC/USDT usando EMAs
        bars = binance.fetch_ohlcv(symbol='BTC/USDT', timeframe='5m', limit=75)
        df_candles = pd.DataFrame(bars, columns=['time', 'abertura','max','min','fechamento','volume'])
        tendencia_alta = False
        tendencia_baixa = False

        emas = [9, 21, 50]
        for ema in emas:
            df_candles[f'EMA_{ema}'] = ta.ema(close=df_candles.fechamento, length=ema)

        if df_candles.iloc[-1]['fechamento'] >= df_candles.iloc[-1]['EMA_50'] and df_candles.iloc[-1]['EMA_9'] > df_candles.iloc[-1]['EMA_21']:
            tendencia_alta = True

        elif df_candles.iloc[-1]['fechamento'] <= df_candles.iloc[-1]['EMA_50'] and df_candles.iloc[-1]['EMA_9'] <= df_candles.iloc[-1]['EMA_21']:
            tendencia_baixa = True
        
        else:
            pass

        # Escolha das Moedas
        stop_loss = 0.015
        take_profit = 0.035
        timeframe = '2h' #1m 1d 1h 15m 30m
        symbols = {'LINK/USDT': 9, 'CHZ/USDT': 1700, '1000SHIB/USDT': 5600,  'TIA/USDT': 21, 'BTC/USDT': 0.002, 'GALAUSDT': 4500, '1000PEPEUSDT': 7500, 'BNB/USDT': 0.23, 'NEAR/USDT': 24,
                    'KSMUSDT': 4,  'AVAXUSDT': 3, '1000FLOKI/USDT': 600, 'NOT/USDT': 20000, 'DOGE/USDT': 350, 'ETH/USDT': 0.045, 'UNIUSDT': 14, 'SNXUSDT': 70, 'GRTUSDT': 650,
                    'BOMEUSDT': 16000, 'FILUSDT': 27, 'RUNEUSDT': 27, 'SUIUSDT': 45}
        
        # importar candles de todos os pares
        hora = datetime.now()
        msg = f'BOT MACD ANÁLISE DO HORÁRIO: {hora.strftime("%H:%M:%S")}'
        print(msg)
        TelegramBot.enviar_msg(msg)
        i = 1

        for symbol in symbols:
            msg = f'Análise {i}/{len(symbols)} - {symbol}'
            print(msg)
            TelegramBot.enviar_msg(msg)
            i = i + 1
            bars = binance.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=100)
            df_candles = pd.DataFrame(bars, columns=['time', 'abertura','max','min','fechamento','volume'])
            df_candles['time'] = pd.to_datetime(df_candles['time'], unit='ms', utc=True).map(lambda x: x.tz_convert('America/Sao_Paulo'))

            # criar métricas da estratégia
            rsi = RSIIndicator(df_candles['fechamento'])
            df_candles['RSI'] = rsi.rsi()
            macd = df_candles.ta.macd(close='fechamento', fast=34, slow=48, signal=30, append=True)

            # condicoes de long e short 
            price = binance.fetch_trades(symbol)[-1]['price']
            price = float(binance.price_to_precision(symbol, price))

            # tamanho posicao max 
            posicao = symbols[symbol]
            posicao_max = posicao
        
            # Abrir long
            if tendencia_alta and df_candles.iloc[-1]['RSI'] >= 50 and df_candles.iloc[-1]['RSI'] <= 70:
                if df_candles.iloc[-1]['MACD_34_48_30'] >= df_candles.iloc[-1]['MACDs_34_48_30'] and df_candles.iloc[-2]['MACD_34_48_30'] <= df_candles.iloc[-2]['MACDs_34_48_30']:
                    if not gr.posicao_max(symbol, posicao_max) and gr.posicoes_abertas(symbol)[0] != 'short' and not gr.ultima_ordem_aberta(symbol):
                        try:
                            # Preço da Moeda
                            altcoin_price = binance.fetch_trades(symbol)[-1]['price']
                            altcoin_price = float(binance.price_to_precision(symbol, altcoin_price))

                            # Preço do Stop
                            altcoin_price_stop_loss = altcoin_price * (1-stop_loss)
                            altcoin_price_stop_loss = float(binance.price_to_precision(symbol, altcoin_price_stop_loss))

                            # Preco do Take Profit
                            altcoin_price_take_profit = altcoin_price * (1+take_profit)
                            altcoin_price_take_profit = float(binance.price_to_precision(symbol, altcoin_price_take_profit))                           

                            #binance.cancel_all_orders(symbol) 
                            binance.create_order(symbol=symbol, side='buy',type='MARKET', amount=posicao, params={'hedged':'true'})
                            binance.create_order(symbol=symbol, side='sell',type='STOP_MARKET', amount=posicao, params= {'stopPrice': altcoin_price_stop_loss})
                            binance.create_order(symbol=symbol, side='sell',type='TAKE_PROFIT_MARKET', amount=posicao, params= {'stopPrice': altcoin_price_take_profit})

                            msg = f'{symbol}: Abrindo long e as operações de stop loss e take profit.'
                            TelegramBot.enviar_msg(msg)
                        except:
                            print("**** Problema ao abrir long! ****")
                            msg = f'Erro ao abrir long em {symbol}'  
                            TelegramBot.enviar_msg(msg)

            elif tendencia_baixa and df_candles.iloc[-1]['RSI'] <= 50 and df_candles.iloc[-1]['RSI'] >= 30:
                if df_candles.iloc[-1]['MACD_34_48_30'] <= df_candles.iloc[-1]['MACDs_34_48_30'] and df_candles.iloc[-2]['MACD_34_48_30'] >= df_candles.iloc[-2]['MACDs_34_48_30']:
                    if not gr.posicao_max(symbol, posicao_max) and gr.posicoes_abertas(symbol)[0] != 'long' and not gr.ultima_ordem_aberta(symbol):
                        try:
                            # Preço da Moeda
                            altcoin_price = binance.fetch_trades(symbol)[-1]['price']
                            altcoin_price = float(binance.price_to_precision(symbol, altcoin_price))

                            # Preço do Stop
                            altcoin_price_stop_loss = altcoin_price * (1+stop_loss)
                            altcoin_price_stop_loss = float(binance.price_to_precision(symbol, altcoin_price_stop_loss))

                            # Preço do Take Profit
                            altcoin_price_take_profit = altcoin_price * (1-take_profit)
                            altcoin_price_take_profit = float(binance.price_to_precision(symbol, altcoin_price_take_profit))     

                            binance.create_order(symbol=symbol, side='sell',type='MARKET', amount=posicao, params={'hedged':'true'})
                            binance.create_order(symbol=symbol, side='buy',type='STOP_MARKET', amount=posicao, params= {'stopPrice': altcoin_price_stop_loss})
                            binance.create_order(symbol=symbol, side='buy',type='TAKE_PROFIT_MARKET', amount=posicao, params= {'stopPrice': altcoin_price_take_profit})
                            msg = f'{symbol}: Abrindo short e as operações de stop loss e take profit.'
                            TelegramBot.enviar_msg(msg)
                        except:
                            print("**** Problema ao abrir short! ****")
                            msg = f'Erro ao abrir short em {symbol}'  
                            TelegramBot.enviar_msg(msg)

            else:
                pass
                # print(f"*** Sem tendencia em {symbol} ***")

            time.sleep(5)
            
    # aglutinar tudo e schedular!
    # ALTERAR PARA 7200 - rodar apenas 1x por hora! #

    tz = pytz.timezone('America/Sao_Paulo')
    def local_time(hour):
        return datetime.now(tz).replace(hour=hour, minute=0, second=0, microsecond=0).strftime('%H:%M')
    
    hours = [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23]

    for hour in hours:
        schedule.every().day.at(local_time(hour)).do(job)

    while True:
        try:
            schedule.run_pending()
        except:
            print('Problemas de conexão...')
            time.sleep(10)

if __name__ == "__main__":
    print("Iniciando o bot...")
    run_bot()