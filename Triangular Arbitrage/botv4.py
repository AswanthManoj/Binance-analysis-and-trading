from itertools import count
import websocket, json
import config
import pandas as pd
import ccxt
from binance.client import Client
from binance.enums import *

client = Client(config.Binance_API_Key, config.Binance_Secret_Key, tld='us')
client.API_URL = 'https://testnet.binance.vision/api'

#get balances for all assets & some account information
#print(client.get_account())

def buy(price, buywith):
    val = buywith/price
    val = val-val*config.trade_fee
    return(val)

def sell(price, sellasset):
    val = price*sellasset
    val = val-val*config.trade_fee
    return(val)

#get balance for a specific asset only (BTC)

_asset = client.get_asset_balance(asset='BTC')
btc = float(_asset.get('free'))
print(btc)
a1 = 0
a2 = btc
a3 = 0
i=0
profit_btc = 0
profitMin = -100
s1s2_aprice = -1
s1s2_bprice = -1
s3s1_aprice = -1
s3s1_bprice = -1
s3s2_aprice = -1
s3s2_bprice = -1
s1 = "ETH"
#s1 = "BNB"
s2 = "BTC"
s3 = "BNB"
#s3 = "LTC"
#s3 = "FTM"
#s3 = "CHR"
#s3 = "GALA"
#s3 = "XRP"
#s3 = "AVAX"

#streaming bnbbtc@bookTicker, xrpbnb@bookTicker, xrpbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/bnbbtc@bookTicker/xrpbnb@bookTicker/xrpbtc@bookTicker"

#streaming bnbbtc@bookTicker, avaxbnb@bookTicker, avaxbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/bnbbtc@bookTicker/avaxbnb@bookTicker/avaxbtc@bookTicker"

#streaming bnbbtc@bookTicker, chrbnb@bookTicker, chrbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/bnbbtc@bookTicker/chrbnb@bookTicker/chrbtc@bookTicker"

#streaming ethbtc@bookTicker, bnbeth@bookTicker, bnbbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@bookTicker/bnbeth@bookTicker/bnbbtc@bookTicker"

#streaming ethbtc@bookTicker, ltceth@bookTicker, ltcbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@bookTicker/ltceth@bookTicker/ltcbtc@bookTicker"

#streaming ethbtc@bookTicker, ftmeth@bookTicker, ftmbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@bookTicker/ftmeth@bookTicker/ftmbtc@bookTicker"

#streaming ethbtc@bookTicker, chreth@bookTicker, chrbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@bookTicker/chreth@bookTicker/chrbtc@bookTicker"

#streaming ethbtc@bookTicker, galaeth@bookTicker, galabtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@bookTicker/galaeth@bookTicker/galabtc@bookTicker"

#streaming ethbtc@bookTicker, xrpeth@bookTicker, xrpbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@bookTicker/xrpeth@bookTicker/xrpbtc@bookTicker"

#streaming ethbtc@bookTicker, avaxeth@bookTicker, avaxbtc@bookTicker at same time
#SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@bookTicker/avaxeth@bookTicker/avaxbtc@bookTicker"

SOCKET = "wss://stream.binance.com:9443/ws/ethbtc@ticker/bnbeth@ticker/bnbbtc@ticker"

print(s3,s1)

def on_open(ws):
    print('opened connection')
def on_close(ws):
    print('closed connection')
def on_message(ws, message):

    json_message = json.loads(message)

    symbol = json_message["s"]
    #bid_price = float(json_message["b"])
    #ask_price = float(json_message["a"])
    market_price = float(json_message["c"])
    print(symbol," : ",market_price)
    global btc, a1, a2, a3, s1, s2, s3, profitMin, profit_btc, s1s2_price, s3s1_price, s3s2_price, i, profitMin
    

    if(symbol==s1+s2 and i==0):#ethbtc
        #s1s2_aprice = ask_price
        #s1s2_bprice = bid_price
        s1s2_price = market_price
        i=i+1
    if(symbol==s3+s1 and i==1):#bnbeth
        #s3s1_aprice = ask_price
        #s3s1_bprice = bid_price
        s3s1_price = market_price
        i=i+1
    if(symbol==s3+s2 and i==2):#bnbbtc
        #s3s2_aprice = ask_price
        #s3s2_bprice = bid_price
        s3s2_price = market_price
        i=i+1
    if(i==3):
        a1 = buy(s1s2_price,a2)#buy eth(s1) with btc(s2)
        a3 = buy(s3s1_price,a1)#buy bnb(s3) with eth(s1)
        a22 = sell(s3s2_price,a3)#sell bnb(s3) for btc(s2)
        profit = a22-a2
        if(profitMin<profit):
            profitMin=profit
            print("Minimum loss : ",profitMin,end = "\r")
        if((profit)>0):
            print("\n",s2," profit : ",profit, end=" ")
            profit_btc = profit_btc+profit
            print("Total profit : ",profit_btc, end=" ")
        else:

            a3 = buy(s3s2_price,a2)#buy bnb(s3) with btc(s2)
            a1 = sell(s3s1_price,a3)#sell bnb(s3) for eth(s1)
            a22 = sell(s1s2_price,a1)#sell eth(s1) for btc(s2)
            profit = a22-a2   
            if(profitMin<profit):
                profitMin=profit
                print("Minimum loss : ",profitMin,end = "\r")         
            if((profit)>0):
                print("\n",s2," profit : ",profit, end=" ")
                profit_btc = profit_btc + profit
                print("Total profit : ",profit_btc, end=" ")
        i=0   


ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)
ws.run_forever()


