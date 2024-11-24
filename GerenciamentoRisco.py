import config as k
import ccxt
import decimal
import time
import TelegramBot


binance = ccxt.binance({'enableRateLimit':True,
                        'apiKey': k.binancekey,
                        'secret': k.binancesecret,
                        'options':{
                            'defaultType': 'future',
                        }
})


def posicoes_abertas(symbol):
    lado = []
    tamanho = []
    preco_entrada = []
    notional = []
    percentage = []
    pnl = []
    bal = binance.fetch_positions(symbols=[symbol])
    for i in bal:
        lado = i['side']
        tamanho = i['info']['positionAmt'].replace('-','')
        notional = i['notional']
        preco_entrada = i['entryPrice']
        percentage = i['percentage']
        pnl = i['info']['unRealizedProfit']

    if lado == 'long':
        pos_aberta = True
    elif lado == 'short':
        pos_aberta = True
    else:
        pos_aberta = False          

    return lado, tamanho, preco_entrada, pos_aberta, notional, percentage, pnl


def livro_ofertas(symbol):
    livro_ofertas = binance.fetch_order_book(symbol)
    bid = decimal.Decimal(livro_ofertas['bids'][0][0])
    ask = decimal.Decimal(livro_ofertas['asks'][0][0])
    return bid, ask


def encerra_posicao(symbol):
    pos_aberta = posicoes_abertas(symbol)[3]
    while pos_aberta == True:
        lado = posicoes_abertas(symbol)[0]
        tamanho = posicoes_abertas(symbol)[1]

        if lado == 'long':
            binance.cancel_all_orders(symbol)
            bid, ask = livro_ofertas(symbol)
            ask = binance.price_to_precision(symbol, ask)
            binance.create_order(symbol, side='sell', type='LIMIT', price=ask, amount=tamanho, params= {'hedged':'true'})
            print(f'Vendendo posição long de {tamanho} moedas de {symbol}')
            # msg = 'Vendendo posiçao...'
            # telegram
            time.sleep(20)

        elif lado == 'short':
            binance.cancel_all_orders(symbol)
            bid, ask = livro_ofertas(symbol)
            bid = binance.price_to_precision(symbol, bid)
            binance.create_order(symbol, side='buy', type='LIMIT', price=bid, amount=tamanho, params= {'hedged':'true'})
            print(f'Comprando posição short de {tamanho} moedas de {symbol}')
            time.sleep(20)
        else:
            print('Impossível encerrar a posição!')

        pos_aberta = posicoes_abertas(symbol=symbol)[3]


def fecha_pnl(symbol, loss, target, timeframe):
    percent = posicoes_abertas(symbol=symbol)[5]
    pnl = posicoes_abertas(symbol=symbol)[6]
    num_timeframe = int(timeframe[:-1])
    unidade = timeframe[-1]

    if percent:
        if percent <= loss:
            print(f'Encerrando posição por loss! {pnl}')
            encerra_posicao(symbol)
            msg = f'LOSS de {pnl} USD'
            TelegramBot.enviar_msg(msg)
            
            if unidade == 'm':
                t_sleep = num_timeframe * 5 * 60
            elif unidade == 'h':
                t_sleep = num_timeframe * 2 * 3600
            elif unidade == 'd':
                t_sleep = num_timeframe * 0.5 * 86400

            time.sleep(t_sleep)
            
        elif percent >= target:
            print(f'Encerra posiçao por gain! {pnl}')
            encerra_posicao(symbol)
            msg = f'GAIN de {pnl} USD'
            TelegramBot.enviar_msg(msg)


def posicao_max(symbol, max_pos):
    pos = posicoes_abertas(symbol)[1]
    if isinstance(pos, list):
        max_posicao = False
    elif float(pos) >= max_pos:
        max_posicao = True
    else:
        max_posicao = False

    return max_posicao


def ultima_ordem_aberta(symbol):
    order = []
    try:
        order = binance.fetch_orders(symbol)[-1]['status']
        if order == 'open':
            open_order = True
        else:
            open_order = False
    except:
        open_order = False                

    return open_order


def stop_dinamico(take_profit, stop_loss):
    bal = binance.fetch_positions()
    symbols = [position['symbol'] for position in bal]

    for symbol in symbols:
        bal = binance.fetch_positions(symbols=[symbol])

        for i in bal:  
            pos = i['info']['positionAmt'].replace('-','')
            entry_price = i['entryPrice']
            lado = i['side']

            if lado == 'long':
                try:
                    take_profit_price = binance.fetch_orders(symbol)[-1]['stopPrice']
                    take_profit_price = float(binance.price_to_precision(symbol, take_profit_price))
                    mark_price = float(i['info']['markPrice']) 
                    
                    var = ((mark_price - entry_price) / entry_price) * 100
                    print('*****')
                    print(f'{symbol}: {var:.2f}% em relação a entrada do {lado}')

                    if ((take_profit_price - mark_price) / mark_price) <= (0.2 * take_profit):
                        binance.cancel_all_orders(symbol)

                        price_att = binance.fetch_trades(symbol)[-1]['price']
                        price_att = float(binance.price_to_precision(symbol, price_att))

                        price_stop_loss = price_att * (1-stop_loss)
                        price_stop_loss = float(binance.price_to_precision(symbol, price_stop_loss))

                        price_take_profit = price_att * (1+take_profit)
                        price_take_profit = float(binance.price_to_precision(symbol, price_take_profit))

                        binance.create_order(symbol=symbol, side='sell',type='STOP_MARKET', amount=pos, params= {'stopPrice': price_stop_loss})
                        binance.create_order(symbol=symbol, side='sell',type='TAKE_PROFIT_MARKET', amount=pos, params= {'stopPrice': price_take_profit})
                        msg = f'Stop loss e Take Profit atualizadas no long em {symbol}'
                        TelegramBot.enviar_msg(msg)

                except: 
                    pass
                    
            else:
                try:
                    take_profit_price = binance.fetch_orders(symbol)[-1]['stopPrice']
                    take_profit_price = float(binance.price_to_precision(symbol, take_profit_price))
                    mark_price = float(i['info']['markPrice']) 

                    var = ((entry_price - mark_price) / mark_price) * 100
                    print('*****')
                    print(f'{symbol}: {var:.2f}% em relação a entrada do {lado}')

                    if ((mark_price - take_profit_price) / take_profit_price) <= (0.2 * take_profit):
                        binance.cancel_all_orders(symbol)

                        price_att = binance.fetch_trades(symbol)[-1]['price']
                        price_att = float(binance.price_to_precision(symbol, price_att))

                        price_stop_loss = price_att * (1 + stop_loss)  
                        price_take_profit = price_att * (1 - take_profit)  

                        binance.create_order(symbol=symbol, side='buy', type='STOP_MARKET', amount=pos, params={'stopPrice': price_stop_loss})
                        binance.create_order(symbol=symbol, side='buy', type='TAKE_PROFIT_MARKET', amount=pos, params={'stopPrice': price_take_profit})
                        msg = f'Stop loss e Take Profit atualizadas no short em {symbol}'
                        TelegramBot.enviar_msg(msg)
                  
                except:
                    pass