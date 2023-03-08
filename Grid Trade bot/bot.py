from mimetypes import init
import websocket, json
import config
from datetime import datetime
from binance.client import Client
from binance.enums import *
import pandas as pd
import ccxt


def close_data(smb):

    exchange = ccxt.binance({
        'apiKey': config.Binance_API_Key,
        'secret': config.Binance_Secret_Key
    })
    exchange.load_markets()
    
    bars1 = exchange.fetch_ohlcv(smb, timeframe=config.TimeFrame, limit=100)
    d = pd.DataFrame(bars1, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    print("close data collected")
    clist = []
    for i in range(len(d['close'])):
        clist.append(d['close'].iloc[i])
    return clist


def macd(dl):
    d = pd.DataFrame(dl, columns =['close'])
    d['ema1'] = d.close.ewm(span = 50, adjust = False).mean()
    d['ema2'] = d.close.ewm(span = 100, adjust = False).mean()
    d['macd'] = d.close.ewm(span = 12, adjust = False).mean() - d.close.ewm(span = 26, adjust = False).mean()
    d['signal'] = d.macd.ewm(span = 9, adjust = False).mean()
    d['histogram'] = d['macd'] - d['signal']
    clist = []
    for i in range(len(d['close'])-1):
        clist.append(d['close'].iloc[i])
    return clist, d["histogram"].iloc[-2], d["histogram"].iloc[-1]


def uptrend_grid(current_price):
    
    cp_u = current_price
    cp_d = current_price
    p_up = config.percentup
    p_down = config.percentdown
    upper_grid = []
    lower_grid = []
    for i in range(30):

        u = (int((cp_u + (p_up * cp_u/100))*1000))/1000
        upper_grid.append(u)
        d = (int((cp_d - (p_down * cp_d/100))*1000))/1000
        lower_grid.append(d)
        cp_u = upper_grid[i]
        cp_d = lower_grid[i]

    lower_grid.reverse()
    return upper_grid, lower_grid



def downtrend_grid(current_price):
    
    cp_u = current_price
    cp_d = current_price
    p_up = config.percentdown
    p_down = config.percentup
    upper_grid = []
    lower_grid = []

    for i in range(30):

        u = (int((cp_u + (p_up * cp_u/100))*1000))/1000
        upper_grid.append(u)
        d = (int((cp_d - (p_down * cp_d/100))*1000))/1000
        lower_grid.append(d)
        cp_u = upper_grid[i]
        cp_d = lower_grid[i]

    lower_grid.reverse()
    return upper_grid, lower_grid



SOCKET = "wss://stream.binance.com:9443/ws/"+config.Symbol+"@kline_"+config.TimeFrame
TRADE_SYMBOL = config.Symbol.upper()
TRADE_SYMBOL = TRADE_SYMBOL[:-4]

Ac_balance = 500
initial_capital = Ac_balance
trade_capital = 20
asset_balance = 0


histogram = 0
s = 0
count = 0
c=0
completed='0'
grids = []
buy_orders = []
sell_orders = []
buyings = []
in_position = 0
invalid = 0
init = True
state = False
trend = ""



client = Client(config.Binance_API_Key, config.Binance_Secret_Key, tld='us', testnet=False)
data = close_data(config.Symbol_for_prev_data)


def on_open(ws):
    stime = datetime.now()
    start_time = stime.strftime("%b-%d-%Y %H:%M:%S")
    print("\n\n\n\n")
    print('opened connection at',start_time)
    print()
    

    
def on_close(ws):
    stime = datetime.now()
    stop_time = stime.strftime("%b-%d-%Y %H:%M:%S")
    print("\n\n\n\n")
    print('closed connection at',stop_time)


def on_message(ws, message):


    global data, s, c, trend, count, completed, in_position, initial_capital, state, init, grids, buy_orders, sell_orders, invalid, Ac_balance, asset_balance, trade_capital, buyings


    json_message = json.loads(message)
    time = int(json_message["E"])
    candle = json_message['k']
    price = float(candle['c'])
    is_candle_closed = candle['x']


    if init:

        data, h0, h1 = macd(data)
        if ((h0 < 0) and (h1 > 0)) or ((h0 > 0) and (h1 > 0)) :
            sell_orders, buy_orders = uptrend_grid(price)
            trend = "u"
            print("trends up")
        elif ((h0 > 0) and (h1 < 0)) or ((h0 < 0) and (h1 < 0)) :
            sell_orders, buy_orders = downtrend_grid(price)
            trend = "d"
            print("trends down")
        grids.append(buy_orders)
        grids.append(price)
        grids.append(sell_orders)
        init = False



    else:
        if state:
            for i in grids:
                if (price > i) and (i != invalid):    
                    buy_orders.append(i)
                elif (price < i) and (i != invalid):
                    sell_orders.append(i)
        
        
        
        state = False
        print("sell order at:{}, price:{}, Invalidated:{}, buy order at:{}, positions:{}".format(sell_orders[0], price, invalid, buy_orders[-1], in_position))
        print("h1 : {}, h2 : {}".format(h0,h1))
        


        if price <= buy_orders[-1]:
            invalid = buy_orders[-1]
            in_position = in_position+1
            Ac_balance = Ac_balance - trade_capital - (trade_capital * config.trade_fee)
            temp = trade_capital/invalid
            buyings.append(temp)
            asset_balance = asset_balance + temp
            print()
            print("Buy at price", invalid)
            print("Current A/C balance is {}, and Asset balance {}".format(Ac_balance, asset_balance))
            print("in_position",in_position)
            buy_orders = []
            sell_orders = []
            state = True



        elif price >= sell_orders[0] and in_position > 0:
            invalid = sell_orders[0]
            in_position = in_position-1
            temp = buyings[-1] * invalid
            Ac_balance = Ac_balance + temp - (temp * config.trade_fee)
            asset_balance = asset_balance - buyings[-1]
            bp = buyings[-1]
            buyings.remove(bp)
            print()
            print("Selling at price", invalid)
            print("Current A/C balance is {}, and Asset balance {}".format(Ac_balance, asset_balance))
            print("in_position",in_position)
            sell_orders=[]
            buy_orders=[]
            state = True
            count+=1
            if count>0 and in_position==0:
                invalid=0
            print("Percentage gain : ", ((Ac_balance-initial_capital)/initial_capital)*100,"%")



    if is_candle_closed:

        print()
        data.loc[len(data.index)] = [price]
        print("Positions:{}, A/C balance:{}, Asset balance:{}".format(in_position,Ac_balance,asset_balance))
        print("Percentage gain : ", ((Ac_balance-initial_capital)/initial_capital)*100,"%")
        data.append(price)
        data, h0, h1 = macd(data)
        if ((h0 < 0) and (h1 > 0)) or ((h0 > 0) and (h1 > 0)) :
            trend2 = "u"
        elif ((h0 > 0) and (h1 < 0)) or ((h0 < 0) and (h1 < 0)) :
            trend2 = "d"
        if not(trend == trend2):
            init = True
        



ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()