###########################################################################_Imports_###########################################################################
import os
import csv
import ccxt
import config
import pandas as pd
import pandas_ta as ta
import websocket, json
from binance.enums import *
from datetime import datetime
from pushbullet import PushBullet
from binance.client import Client
from ta.volatility import AverageTrueRange
from binance.exceptions import BinanceAPIException, BinanceOrderException

########################################################################_Authentication_#######################################################################
try:
    client = Client(config.Binance_API_Key, config.Binance_Secret_Key, testnet=False)                                                                             
    exchange = ccxt.binance({ 'apiKey': config.Binance_API_Key, 'secret': config.Binance_Secret_Key})                                                              
    exchange.load_markets()
    pb = PushBullet(config.pushbulletToken)
except Exception as e:
    print(e)

##########################################################################_Functions_##########################################################################

#general functions
def sendNotification(_message: str):
    try:
        push = pb.push_note(title, _message)
    except:
        pass

def supertrend(df, period=100, atr_multiplier=3.46):
    try:
        d=ta.supertrend(df['high'], df['low'], df['close'], length=period, multiplier=atr_multiplier)
        return d[d.columns[0]]
    except Exception as e:
        print('Error in supertrend',e)

def getAcBalance(base: str):
    try:
        balance = client.get_asset_balance(asset=base)
        return float(balance['free'])
    except Exception as e:
        print(e)

def topup_bnb(min_balance: float, topup: float):
    # Top up BNB balance if it drops below minimum specified balance
    bnb_balance = client.get_asset_balance(asset='BNB')
    bnb_balance = float(bnb_balance['free'])
    if bnb_balance < min_balance:
        qty = round(topup - bnb_balance, 5)
        print(qty)
        order = client.order_market_buy(symbol='BNBUSDT', quantity=qty)
        return order
    return False

def getPrecision(side: str, symbol):
    exchangeinfo = client.get_exchange_info()
    for sm in exchangeinfo['symbols']:
        if(sm['symbol'] == symbol):
            if(side=='sell'):
                for filter in sm['filters']:
                    if(filter['filterType']=='LOT_SIZE'):
                        pre = filter['stepSize'].split('1')[0]
                        pre = pre.split('.')[1]
                        pre = len(pre)+1
                        return pre
            else:
                return int( sm['quoteAssetPrecision'] )

def truncateToPrecision(val: str, ndigits: str):  
    try: 
        if 'e' in val:
            integerPart, decimalPart = val.split('.')
            decimalPart, expo = decimalPart.split('e-')
            exponant = int(exponant)
            val = '0.'+(exponant-1)*'0'+integerPart+decimalPart
        
        integerPart,decimalPart = val.split('.')
        val = integerPart+'.'+decimalPart[:ndigits]
        return val   
                
    except:
        print('Error in truncating')

def log(content: str):
    try:
        _filename = 'TradeData.txt'
        stime = datetime.now()
        start_time = stime.strftime("%b-%d-%Y %H:%M:%S")
        f = open(_filename, "a")
        f.write(str(start_time)+' : '+content+'\n')
        f.close()
    except Exception as e:
        print('Error while loging data',e)

def loadData(s, timeframe: str, symbol, limit=1000):
    try:
        _filename = '_market_data_csv/'+s+'_'+timeframe
        bars1 = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        d = pd.DataFrame(bars1, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        p = d['close'].iloc[-1]
        t = d['time'].iloc[-1]
        rnd = len(str(d['close'].iloc[0]).split('.')[1])
        d = d.iloc[:-1]
        d.to_parquet(_filename+'.gzip',compression='gzip')
        return float(p),t,rnd
    except Exception as e:
        print('Error while loading data',e)

'''def update(data, symbol, timeframe):
    try:
        _filename = '_market_data_csv/'+symbol+'_'+timeframe
        d = pd.read_parquet(_filename+'.gzip')
        new_row = {'time':data['t'], 'open':float(data['o']), 'high':float(data['h']), 'low':float(data['l']), 'close':float(data['c']), 'volume':float(data['v'])}
        d2=pd.DataFrame(new_row, index=[len(d)])
        d = pd.concat([d, d2], ignore_index = True)
        if len(d)>999:
            d.drop([0],axis=0,inplace=True)
            d.reset_index(inplace=True)
            print(d)
        else:
            d.reset_index(inplace=True)
        d.to_parquet(_filename+'.gzip',compression='gzip')
    except Exception as e:
        print('Error while updating data',e)'''
    
def analyse(symbol, timeframe, data):
    global signal_data, asset_data, inPosition
    try:
        _filename = '_market_data_csv/'+symbol+'_'+timeframe
        d = pd.read_parquet(_filename+'.gzip')
        if(type(data)!=str):
            new_row = {'time':data['t'], 'open':float(data['o']), 'high':float(data['h']), 'low':float(data['l']), 'close':float(data['c']), 'volume':float(data['v'])}
            d2=pd.DataFrame(new_row, index=[len(d)])
            d = pd.concat([d, d2], ignore_index = True)
            d.reset_index()
            #_filename = '_market_data_csv/'+symbol+'_'+timeframe
            #d = pd.read_parquet(_filename+'.gzip')
        dm = pd.DataFrame()
        dm['time'] = d['time']
        rnd = len(str(d['close'].iloc[34]).split('.')[1])
        dm['close'] = round(((d['open'] + d['high'] + d['low'] + d['close'])/4),rnd)
        for i in range(len(d)):
            if i == 0:
                dm.at[0,'open'] = round(((d['open'].iloc[0] + d['close'].iloc[0])/2),rnd)
            else:
                dm.at[i,'open'] = round(((dm.at[i-1,'open'] + dm.at[i-1,'close'])/2),rnd)
        dm['high'] = dm.loc[:,['open', 'close']].join(d['high']).max(axis=1)
        dm['low'] = dm.loc[:,['open', 'close']].join(d['low']).min(axis=1)        
        d.to_parquet(_filename+'.gzip',compression='gzip')
        #macd
        dm['ema1'] = dm.close.ewm(span = 50, adjust = False).mean()
        dm['ema2'] = dm.close.ewm(span = 100, adjust = False).mean()
        dm['macd'] = dm.close.ewm(span = 12, adjust = False).mean() - dm.close.ewm(span = 26, adjust = False).mean()
        dm['sig'] = dm.macd.ewm(span = 9, adjust = False).mean()
        #atr
        atr = AverageTrueRange(dm['high'],dm['low'],dm['close'],window=config.atr_period_for_sig)
        dm['atr'] = atr.average_true_range()
        dm['atrn'] = dm['atr']*(-config.atr_tune_val)
        dm['atr_avg'] = (dm.atrn.ewm(span = config.atr_avg_length, adjust = False).mean())-dm['sig']
        dm['hist'] = dm['sig']-dm['atr_avg']
        dm['stoploss'] = dm['close']-(config.atrStoploss*dm['atr'])
        dm['stoploss_trailing'] = dm['close']-(config.atr_scaleFactor_trailing*dm['atr'])
        dm['takeprofit'] = dm['close']+(config.atrTakeprofit*dm['atr'])
        dm['bline'] = (dm['hist']*-1.5)
        dm['baseline'] = dm['bline'].rolling(600).mean()
        #trailing stoploss
        if (inPosition['inTrade']==True) and (inPosition['symbol']==symbol):
            if dm['hist'].iloc[-1]>0 and dm['hist'].iloc[-2]<0 and inPosition['trailing_switch']==1:
                inPosition['trailing_switch']=2
                asset_data[symbol]['trailing']=dm['stoploss'].iloc[-1]
            if inPosition['trailing_switch']==1:
                trailing = max(asset_data[symbol]['trailing'],dm['stoploss_trailing'].iloc[-1])
            elif inPosition['trailing_switch']==2:
                trailing = max(asset_data[symbol]['trailing'],dm['stoploss'].iloc[-1])
            else:
                trailing=0
            #if(dm['close'].iloc[-1]<trailing):
            #    signal_data[symbol]=False
        else:
            trailing=0
        if (dm['hist'].iloc[-3]>dm['hist'].iloc[-2]) and (dm['hist'].iloc[-2]<dm['hist'].iloc[-1]):
            if (dm['hist'].iloc[-3]<0) and (dm['hist'].iloc[-2]<0) and (dm['hist'].iloc[-3]<dm['baseline'].iloc[-3]) and (dm['hist'].iloc[-2]<dm['baseline'].iloc[-2]) and (dm['hist'].iloc[-1]<dm['baseline'].iloc[-1]):
                    signal_data[symbol] = True
                    inPosition['trailing_switch'] = 1
        return ( float(dm['stoploss'].iloc[-1]), float(dm['takeprofit'].iloc[-1]), float(trailing) )

    except Exception as e:
        print('Error in analyse',e)

#def _createtrackfile():
#    _filename = '_track_performance.csv'
#    with open(_filename, 'w', newline='') as csvfile:
#        csvwriter = csv.writer(csvfile)
#        csvwriter.writerow(['time', 'market', 'bot'])
#        csvfile.close()

#test functions
def _placeTestOrder(symbol, price: float, side: str, qnt: float):
    try:
        if side == 'buy':
            val = qnt/price
            val = val-val*config.trade_fee
            return(val)
        else:
            val = price*qnt
            val = val-val*config.trade_fee
            return(val)
    except Exception as e:
        print('Error in _placeTestOrder',e)

def _test_message(orderData, msg: str, profit=0):
    if(msg=='partial profit'):
        txt='TAKEN PARTIAL PROFIT\n'
        txt=txt+'Updated Order Data\n'
        txt=txt+'Asset quantity : '+str(orderData['assetQuantity'])+'\n'
        txt=txt+'Take Profit : '+str(orderData['takeprofit'])+'\n'
        txt=txt+'Stop Loss : '+str(orderData['stoploss'])
    elif(msg=='bought'):
        txt='ASSET BOUGHT\n'
        txt=txt+'Asset quantity : '+str(orderData['assetQuantity'])+'\n'
        txt=txt+'Asset buy price : '+str(orderData['price'])+'\n'
        txt=txt+'Take Profit : '+str(orderData['takeprofit'])+'\n'
        txt=txt+'Stop Loss : '+str(orderData['stoploss'])
    elif(msg=='sold'):
        txt='ASSET SOLD\n'
        txt=txt+'Current account balance : $'+str(config.AcBalance)+'\n'
        txt=txt+'Profit gain : $'+str(profit)+'\n'
        txt=txt+'Success trades : '+str(config.tradeData['successfull'])+'\n'
        txt=txt+'Failed trades : '+str(config.tradeData['failed'])
    elif(msg=='stoploss'):
        txt='ASSET SOLD, PRICE REACHED STOPLOSS\n'
        txt=txt+'Current account balance : $'+str(config.AcBalance)+'\n'
        txt=txt+'Profit gain : $'+str(profit)+'\n'
        txt=txt+'Success trades : '+str(config.tradeData['successfull'])+'\n'
        txt=txt+'Failed trades : '+str(config.tradeData['failed'])
    elif(msg=='profit'):
        txt='ASSET SOLD, PROFIT TAKEN\n'
        txt=txt+'Current account balance : $'+str(config.AcBalance)+'\n'
        txt=txt+'Profit gain : $'+str(profit)+'\n'
        txt=txt+'Success trades : '+str(config.tradeData['successfull'])+'\n'
        txt=txt+'Failed trades : '+str(config.tradeData['failed'])
    return txt

def _test_checkBuy(symbol, price: float):
    global orderData, inPosition, asset_data, base, quote
    try:
        #stlos_atr=round(asset_data['stoploss'],price_precisions)
        stlos_atr = float(truncateToPrecision( str(asset_data[symbol]['stoploss']), price_precisions[symbol] ))
        #tkpro_atr=round(asset_data['takeprofit'],price_precisions)
        tkpro_atr = float(truncateToPrecision( str(asset_data[symbol]['takeprofit']), price_precisions[symbol] ))
        percent = ((tkpro_atr-price)/price)*100
        if percent>0.2:
            inPosition['symbol'] = symbol
            inPosition['inTrade'] = True
            inPosition['tradeSwitch']=1
            orderData['assetQuantity'] = _placeTestOrder(symbol, price, 'buy', config.tradeCapital)
            orderData['price'] = price
            orderData['takeprofit'] = tkpro_atr
            orderData['stoploss'] = stlos_atr
            base = symbol.upper()
            quote = symbol.upper()
            return True
        else:
            signal_data[symbol]==False
            inPosition['trailing_switch']=0
            return False
    except Exception as e:
        print('Error in _test_checkBuy',e)    

def _test_takeprofit(symbol, price: float):
    global orderData, inPosition, asset_data, usdt_test_profits, signal_data
    try:
        if (inPosition['tradeSwitch']==1):
            usdt_test_profits = _placeTestOrder(symbol, price, 'sell', (orderData['assetQuantity']))
            orderData['assetQuantity'] = 0
            orderData['price'] = 0
            orderData['stoploss'] = 0
            orderData['takeprofit'] = 0
            profit = usdt_test_profits-config.tradeCapital
            if profit>=0:
                config.tradeData['successfull'] = config.tradeData['successfull']+1
            else:
                config.tradeData['failed'] = config.tradeData['failed']+1
            config.AcBalance = config.AcBalance+profit
            inPosition['inTrade'] = False
            inPosition['tradeSwitch'] = 0
            signal_data[inPosition['symbol']] = False
            inPosition['symbol'] = ''
            usdt_test_profits = 0
            inPosition['trailing_switch']=0
            for s in config.symbols:
                signal_data[s]=False
            return profit
    except Exception as e:
        print('Error in _test_takeprofit',e)
    
def _test_stoploss(symbol, price: float):
    global orderData, inPosition, asset_data, usdt_test_profits, signal_data
    try:
        usdt_test_profits = _placeTestOrder(symbol,price,'sell',orderData['assetQuantity'])
        orderData['assetQuantity'] = 0
        orderData['price'] = 0
        orderData['stoploss'] = 0
        orderData['takeprofit'] = 0
        profit = usdt_test_profits-config.tradeCapital
        if profit>=0:
            config.tradeData['successfull'] = config.tradeData['successfull']+1
        else:
            config.tradeData['failed'] = config.tradeData['failed']+1
        config.AcBalance = config.AcBalance+profit
        usdt_test_profits=0
        inPosition['inTrade'] = False
        signal_data[inPosition['symbol']] = False
        inPosition['tradeSwitch']=0
        inPosition['symbol'] = ''
        inPosition['trailing_switch']=0
        for s in config.symbols:
            signal_data[s]=False
        return profit
    except Exception as e:
        print('Error in _test_stoploss',e)
    
def _test_checkSell(symbol, price: float):
    global orderData, inPosition, asset_data, usdt_test_profits, signal_data
    try:
        signal_data[inPosition['symbol']]=False
        inPosition['symbol'] = ''
        inPosition['inTrade'] = False
        inPosition['tradeSwitch']=0
        usdt_test_profits = _placeTestOrder(symbol,price,'sell',orderData['assetQuantity'])
        orderData['assetQuantity'] = 0
        orderData['price'] = 0
        orderData['stoploss'] = 0
        orderData['takeprofit'] = 0
        inPosition['trailing_switch']=0
        profit = usdt_test_profits-config.tradeCapital
        if profit>=0:
            config.tradeData['successfull'] = config.tradeData['successfull']+1
        else:
            config.tradeData['failed'] = config.tradeData['failed']+1
        config.AcBalance = config.AcBalance+profit
        usdt_test_profits = 0
        for s in config.symbols:
            signal_data[s]=False
        return profit
    except Exception as e:
        print('Error in _test_checkBuy',e)

def _testtrackPerformance(time,price):
    try:
        _filename = '_track_performance.csv'
        d = pd.read_csv(_filename)
        new_row = { 'time':time, 'market':(price*config.assetForTracking), 'bot':config.AcBalance }
        d2=pd.DataFrame(new_row, index=[len(d)])
        d = pd.concat([d, d2], ignore_index = True)
        d.reset_index()
        d.to_csv(_filename,index=False)
    except Exception as e:
        print('Error in _testtrackPerformance ',e)

'''
#main functions
def placeMarketOrder(symbol: str, side: str, qnt: str):
    try:
        if side == 'buy':
            qnt = truncateToPrecision(qnt, getPrecision(side='buy', symbol=symbol))
            order = client.order_market_buy(symbol=symbol, quoteOrderQty=qnt)
        else:
            qnt = truncateToPrecision(qnt, getPrecision(side='sell', symbol=symbol))
            order = client.order_market_sell(symbol=symbol, quantity=qnt)
        return order
    except BinanceAPIException as e:
        # error handling goes here
        print(e)
    except BinanceOrderException as e:
        # error handling goes here
        print(e) 
    
def _message(orderData, msg: str, profit=0):
    if(msg=='partial profit'):
        txt='TAKEN PARTIAL PROFIT\n'
        txt=txt+'Updated Order Data\n'
        txt=txt+'Asset quantity : '+str(orderData['assetQuantity'])+'\n'
        txt=txt+'Take Profit : '+str(orderData['takeprofit'])+'\n'
        txt=txt+'Stop Loss : '+str(orderData['stoploss'])
    elif(msg=='bought'):
        txt='ASSET BOUGHT\n'
        txt=txt+'Asset quantity : '+str(orderData['assetQuantity'])+'\n'
        txt=txt+'Asset buy price : '+str(orderData['price'])+'\n'
        txt=txt+'Take Profit : '+str(orderData['takeprofit'])+'\n'
        txt=txt+'Stop Loss : '+str(orderData['stoploss'])
    elif(msg=='sold'):
        txt='ASSET SOLD\n'
        txt=txt+'Current account balance : $'+str(getAcBalance(QUOTE_SYMBOL))+'\n'
        txt=txt+'Profit gain : $'+str(profit)+'\n'
        txt=txt+'Success trades : '+str(config.tradeData['successfull'])+'\n'
        txt=txt+'Failed trades : '+str(config.tradeData['failed'])
    elif(msg=='stoploss'):
        txt='ASSET SOLD, PRICE REACHED STOPLOSS\n'
        txt=txt+'Current account balance : $'+str(getAcBalance(QUOTE_SYMBOL))+'\n'
        txt=txt+'Profit gain : $'+str(profit)+'\n'
        txt=txt+'Success trades : '+str(config.tradeData['successfull'])+'\n'
        txt=txt+'Failed trades : '+str(config.tradeData['failed'])
    elif(msg=='profit'):
        txt='ASSET SOLD, PROFIT TAKEN\n'
        txt=txt+'Current account balance : $'+str(getAcBalance(QUOTE_SYMBOL))+'\n'
        txt=txt+'Profit gain : $'+str(profit)+'\n'
        txt=txt+'Success trades : '+str(config.tradeData['successfull'])+'\n'
        txt=txt+'Failed trades : '+str(config.tradeData['failed'])
    return txt

def checkBuy(symbol, price: float):
    global orderData,inPosition, asset_data, base, quote, prevBal
    try:
        stlos_atr=round(asset_data[symbol]['stoploss'],price_precisions[symbol])
        tkpro_atr=round(asset_data[symbol]['takeprofit'],price_precisions[symbol])
        inPosition['symbol'] = symbol
        base = symbol[:-4].upper()
        quote = symbol[-4:].upper()
        prevBal = getAcBalance(quote)
        config.AcBalance = prevBal
        inPosition['inTrade'] = True
        inPosition['tradeSwitch']=1
        orderData['position'] = True
        order = placeMarketOrder(symbol.upper(),'buy',str(config.tradeCapital))
        orderData['assetQuantity'] = float( order['fills'][0]['qty'] )
        orderData['price'] = float( order['fills'][0]['price'] )
        orderData['takeprofit'] = tkpro_atr
        orderData['stoploss'] = stlos_atr
    except Exception as e:
        print('Error in checkBuy',e)

def takeprofit(symbol, price: float):
    global orderData,inPosition, asset_data, quote, base, prevBal
    try:
        if (inPosition['tradeSwitch']==1):
            order = placeMarketOrder(symbol.upper(),'sell',str(orderData['assetQuantity']/3))
            orderData['assetQuantity'] = 2*(orderData['assetQuantity']/3)
            orderData['stoploss'] = asset_data[symbol]['trailing']
            orderData['takeprofit'] = (2*orderData['takeprofit'])-orderData['price']
            inPosition['tradeSwitch'] = 2
        elif (inPosition['tradeSwitch']==2):
            order = placeMarketOrder(symbol.upper(),'sell',str(orderData['assetQuantity']/2))
            orderData['assetQuantity'] = (orderData['assetQuantity']/2)
            orderData['stoploss'] = asset_data[symbol]['trailing']
            orderData['takeprofit'] = asset_data[symbol]['trailing']*1.5
            inPosition['tradeSwitch'] = 3
        elif (inPosition['tradeSwitch']==3):
            order = placeMarketOrder(symbol.upper(),'sell',str(orderData['assetQuantity']))
            orderData['position'] = False
            orderData['assetQuantity'] = 0
            orderData['price'] = 0
            orderData['stoploss'] = 0
            orderData['takeprofit'] = 0
            profit = getAcBalance(quote)-prevBal
            if profit>=0:
                config.tradeData['successfull'] = config.tradeData['successfull']+1
            else:
                config.tradeData['failed'] = config.tradeData['failed']+1
            config.AcBalance = config.AcBalance+profit
            inPosition['inTrade'] = False
            inPosition['tradeSwitch'] = 0
            signal_data[symbol] = False
            inPosition['symbol'] = ''
            return profit
    except Exception as e:
        print('Error in _test_takeprofit',e)

def stoploss(symbol, price: float):
    global orderData,inPosition, asset_data, prevBal, quote, base
    try:
        order = placeMarketOrder(inPosition['symbol'].upper(),'sell',str(orderData['assetQuantity']))
        profit = getAcBalance(quote)-prevBal
        if profit>=0:
            config.tradeData['successfull'] = config.tradeData['successfull']+1
        else:
            config.tradeData['failed'] = config.tradeData['failed']+1
        config.AcBalance = config.AcBalance+profit
        orderData['position'] = False
        orderData['assetQuantity'] = 0
        orderData['price'] = 0
        orderData['stoploss'] = 0
        orderData['takeprofit'] = 0
        inPosition['inTrade'] = False
        inPosition['tradeSwitch'] = 0
        signal_data[inPosition['symbol']] = False
        inPosition['symbol'] = ''
        return profit
    except Exception as e:
        print('Error in stoploss',e)

def checkSell(symbol, price: float):
    global orderData,inPosition, asset_data, base, quote, prevBal
    try:
        signal_data[inPosition['symbol']]=False
        inPosition['inTrade'] = False
        inPosition['tradeSwitch']=0
        order = placeMarketOrder(inPosition['symbol'].upper(),'sell',str(orderData['assetQuantity']))
        inPosition['symbol'] = ''
        orderData['position'] = False
        orderData['assetQuantity'] = 0
        orderData['price'] = 0
        orderData['stoploss'] = 0
        orderData['takeprofit'] = 0
        profit = getAcBalance(quote)-prevBal
        if profit>=0:
            config.tradeData['successfull'] = config.tradeData['successfull']+1
        else:
            config.tradeData['failed'] = config.tradeData['failed']+1
        config.AcBalance = config.AcBalance+profit
        return profit
    except Exception as e:
        print('Error in checkSell',e)

def trackPerformance(time,price,_filename):
    try:
        _filename = _filename+'_track_performance.csv'
        d = pd.read_csv(_filename)
        new_row = {'time':time, 'market':(price*config.Asset_for_tracking), 'bot':getAcBalance(QUOTE_SYMBOL)}
        d2=pd.DataFrame(new_row, index=[len(d)])
        d = pd.concat([d, d2], ignore_index = True)
        d.reset_index()
        d.to_csv(_filename,index=False)
    except Exception as e:
        print('Error in trackPerformance ',e)
'''
#websocket functions
def on_open(ws):
    stime = datetime.now()
    start_time = stime.strftime("%b-%d-%Y %H:%M:%S")
    print('opened connection at',start_time)
    sendNotification('opened connection')

def on_message(ws, message):
    global timeFrameData, orderData, inPosition, asset_data, signal_data, title, price_precisions, usdt_test_profits, prevBal
    try:
        json_message = json.loads(message)
        time = int(json_message["E"])
        candle = json_message['k']
        #tframe = candle['i']
        price = float(candle['c'])
        is_candle_closed = candle['x']
        smb=candle['s'].lower()
        _round_precision = len(str(price).split('.')[1])
       
        if config.isTest:

            if (is_candle_closed==True):
                #update(candle,smb,config.timeFrame)
                asset_data[smb]['stoploss'], asset_data[smb]['takeprofit'], asset_data[smb]['trailing'] = analyse(smb,config.timeFrame,candle)
                price_precisions[smb] = max( price_precisions[smb], _round_precision )

            if (inPosition['inTrade']==False):
                if (inPosition['tradeSwitch']==0) and (signal_data[smb]==True):
                    if( config.AcBalance>(1.1*config.tradeCapital) ): 
                        if _test_checkBuy(smb,price):
                            log(inPosition['symbol']+'\n'+str(orderData))
                            print(inPosition['symbol']+' bought', orderData)
                            sendNotification(_test_message(orderData,'bought'))
                    else:
                        print('Account balance is less than trade capital')
                        sendNotification('Account balance is less than trade capital')
            else: 
                if (smb==inPosition['symbol']) and (is_candle_closed==True): 
                    if (inPosition['trailing_switch']==1):
                        sl = float(truncateToPrecision( str(asset_data[inPosition['symbol']]['trailing']), price_precisions[inPosition['symbol']] ))
                        orderData['stoploss'] = max(sl,orderData['stoploss'])   
                        percent = ((orderData['price']-orderData['stoploss'])/orderData['price'])*100
                        if percent>=0.15:
                            inPosition['trailing_switch']=2
                    elif (inPosition['trailing_switch']==2):
                        sl = float(truncateToPrecision( str(asset_data[inPosition['symbol']]['trailing']), price_precisions[inPosition['symbol']] ))
                        orderData['stoploss'] = max(sl,orderData['stoploss'])
                if (smb==inPosition['symbol']) and (price>=orderData['takeprofit']):
                    profit = _test_takeprofit(inPosition['symbol'],price) 
                    print('Profit taken', profit, config.tradeData, config.AcBalance) 
                    log('Final profit taken\n'+'Profit : '+str(profit)+'Account Balance : '+str(config.AcBalance)+str(config.tradeData)+'\n')
                    sendNotification(_test_message(orderData,'profit', profit))
                elif(smb==inPosition['symbol']) and (price <= orderData['stoploss']):
                    profit = _test_stoploss(inPosition['symbol'],price) 
                    print('stoploss hit', profit, config.tradeData, config.AcBalance) 
                    log('Stoploss hit\n'+'Profit/Gain : '+str(profit)+'Account Balance : '+str(config.AcBalance)+str(config.tradeData)+'\n')
                    sendNotification(_test_message(orderData,'stoploss', profit))
                    
                    

        '''else:
            if inPosition['symbol']==smb and inPosition['inTrade']:

                if inPosition['tradeSwitch']==1:   
                    if is_candle_closed and asset_data[smb]['trailing']<price:
                        orderData['stoploss'] = asset_data[smb]['trailing'] 
                    if( price>=orderData['takeprofit'] ):
                        takeprofit(smb,price)
                        print('First partial profit taken', config.orderData) 
                    elif( price <= orderData['stoploss'] ):
                        profit = stoploss(smb,price) 
                        print('stoploss hit', profit, config.tradeData, config.AcBalance) 
                        _testtrackPerformance(smb,time,price)
                    #elif (signal_data[smb]==False) and is_candle_closed :
                    #    profit = checkSell(smb,price) 
                    #    print('signal reverted', profit, config.tradeData, config.AcBalance) 
                    #    _testtrackPerformance(smb,time,price)

                elif inPosition['tradeSwitch']==2:
                    if is_candle_closed and asset_data[smb]['trailing']<price:
                        orderData['stoploss'] = asset_data[smb]['trailing'] 
                    if( price>=orderData['takeprofit'] ):
                        takeprofit(smb,price)
                        print('Second partial profit taken', config.orderData) 
                    elif( (price <= orderData['stoploss']) and is_candle_closed ):
                        profit = stoploss(smb,price) 
                        print('stoploss hit', profit, config.tradeData, config.AcBalance) 
                        _testtrackPerformance(smb,time,price)

                elif inPosition['tradeSwitch']==3: 
                    if is_candle_closed:
                        if asset_data[smb]['trailing']<price:
                            orderData['stoploss'] = asset_data[smb]['trailing']
                            orderData['takeprofit'] = asset_data[smb]['trailing']*1.5
                        if( price <= orderData['stoploss'] ):
                            profit = stoploss(smb,price) 
                            print('Profit taken', profit, config.tradeData, config.AcBalance) 
                            _testtrackPerformance(smb,time,price)
            
            if is_candle_closed:
                for symbol in config.symbols:
                    if (smb==symbol):
                        update(candle,symbol)
                        asset_data[symbol]['stoploss'], asset_data[symbol]['takeprofit'], asset_data[symbol]['trailing'] = analyse(symbol)
                        price_precisions[symbol] = max( price_precisions[symbol], _round_precision )
                        if (not inPosition['inTrade']):
                            if (signal_data[symbol]==True) and (inPosition['tradeSwitch']==0):
                                if( config.AcBalance>(1.1*config.tradeCapital) ): 
                                    checkBuy(symbol,price)
                                    sendNotification(smb+' bought')
                                    print(inPosition['symbol']+' bought', orderData)
                                else:
                                    print('Account balance is less than trade capital')
                                    sendNotification('Account balance is less than trade capital')'''
            
    
    except Exception as e:
        print('Error in on_message',e)

def on_close(ws):
    print('closed connection')
    log('closed connection')
    sendNotification('Connection closed')

############################################################################_Main_#############################################################################

#global variables
global base, quote, orderData, inPosition, asset_data, signal_data, title, price_precisions, usdt_test_profits, prevBal
title = 'SCALPER_BOT_'
ast_data = {                                                                                                                                                   
    'stoploss'      : 0.0,
    'takeprofit'    : 0.0,
    'trailing'      : 0.0                                                                                                                              
}
signal_data={}
asset_data={}
price_precisions={}
trailing_switch=0
inPosition={'symbol':'','inTrade':False,'tradeSwitch':0,'trailing_switch':0}
orderData = {'assetQuantity':0.0, 'price':0.0, 'stoploss':0.0, 'takeprofit':0.0} 
usdt_test_profits=0                                                                                                                                                                                                                                                                                                                   
try:
    os.mkdir('_market_data_csv')
    for symbol in config.symbols:
        asset_data[symbol]=ast_data
        signal_data[symbol]=False
        price_precisions[symbol]=0
except :
    pass

#drive_code
if(config.isTest):
    while(True):                                                                                                                                                                
        try:                                                                                                                                                                       
            if( config.AcBalance>(1.1*config.tradeCapital) ):                                                                                                                                                                                             
                ##################################################################Loading initial data###################################################################
                url="wss://stream.binance.com:9443/ws/"
                for symbol in config.symbols:
                    symbol_prev = symbol.upper()
                    symbol_prev=symbol_prev[:-4]+'/'+symbol_prev[-4:]
                    p,t,price_precisions[symbol]=loadData(symbol,config.timeFrame,symbol=symbol_prev)
                    url=url+symbol+"@kline_"+config.timeFrame+"/"
                    asset_data[symbol]['stoploss'], asset_data[symbol]['takeprofit'], asset_data[symbol]['trailing'] = analyse(symbol,config.timeFrame,'none')
                                                                                                                                                                                                                                           
                ###################################################################Socket connection#####################################################################                                                                                                                                                                    
                SOCKET=url[:-1]                                                                                                                                                                                                 
                ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)                                                                
                ws.run_forever()
                                                                                                                                                
            else:                                                                                                                                                             
                print('Account balance is less than trade balance')                                                                                                          
        except Exception as e:                                                                                                                                                               
            print("Reconnecting",e)
'''
else:
    prevBal= getAcBalance(quote)
    prevBal=config.AcBalance
    while(True):                                                                                                                                                                
        try:                                                                                                                                                                       
            if( prevBal>(1.1*config.tradeCapital) ):                                                                                                                                                                                             
                ##################################################################Loading initial data###################################################################
                url="wss://stream.binance.com:9443/ws/"
                _createtrackfile()
                for symbol in config.symbols:
                    symbol_prev = symbol.upper()
                    symbol_prev=symbol_prev[:-4]+'/'+symbol_prev[-4:]
                    p,t=loadData(symbol,config.timeFrame,symbol=symbol_prev)
                    url=url+symbol+"@kline_"+config.timeFrame+"/"
                    config.Asset_for_tracking[symbol]=config.AcBalance/(p*len(config.symbols)) 
                    _testtrackPerformance(symbol,t,p)  
                    asset_data[symbol]['stoploss'], asset_data[symbol]['takeprofit'], asset_data[symbol]['trailing'] = analyse(symbol)
                                                                                                                                                                                                                                           
                ###################################################################Socket connection#####################################################################                                                                                                                                                                    
                SOCKET=url[:-1]                                                                                                                                                                                                 
                ws = websocket.WebSocketApp(SOCKET, on_open=on_open, on_close=on_close, on_message=on_message)                                                                
                ws.run_forever()
                                                                                                                                                
            else:                                                                                                                                                             
                print('Account balance is less than trade balance')                                                                                                          
        except Exception as e:                                                                                                                                                               
            print("Reconnecting",e)
'''