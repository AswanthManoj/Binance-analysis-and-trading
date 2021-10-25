import config
import ccxt
import pandas as pd

Trending_assets = []
exchange = ccxt.binance({
    'apiKey': config.Binance_Test_API_Key,
    'secret': config.Binance_Test_Secret_Key
})


def get_prev_data(exchange,smb,T_frame1,T_frame2,Limit):
    exchange.load_markets()
    
    bars1 = exchange.fetch_ohlcv(smb, timeframe=T_frame1, limit=Limit)
    df1 = pd.DataFrame(bars1, columns=['time', 'open', 'high', 'low', 'close', 'volume']) 

    bars2 = exchange.fetch_ohlcv(smb, timeframe=T_frame2, limit=Limit)
    df2 = pd.DataFrame(bars2, columns=['time', 'open', 'high', 'low', 'close', 'volume']) 
    
    return df1, df2

def analytic(data):
    d = pd.DataFrame()
    d = data
    d['ema1'] = d.close.ewm(span = 50, adjust = False).mean()
    d['ema2'] = d.close.ewm(span = 100, adjust = False).mean()

    return d.iloc[-1]   

def Find_trending_asset():
    for symbol in config.Symbol_list:
        data1, data2 = get_prev_data(exchange,symbol,config.TimeFrame1,config.TimeFrame2, config.Limit)
        final_data1 =analytic(data1)
        final_data2 = analytic(data2)

        if final_data1['ema1'] > final_data1['ema2']:
            if final_data2['ema1'] > final_data2['ema2']:
                Trending_assets.append(symbol)

    if Trending_assets == []:
        print("No assets are trending")
    else:
        print("List of Trending assets")
        for s in Trending_assets:
            print(s)
            
Find_trending_asset()
