import pandas as pd
import ccxt
import os, config
import websocket, json
from datetime import datetime
from binance.enums import *
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceOrderException
import threading
from indicator import indicators
from strategies import tradeStrategy





###################################################################'''Exchange connection'''###################################################################


class cryptoExchange():


    def __init__(self, apiKey: str, apiSecret: str, testnet: bool):

        self.apiKey = apiKey
        self.apiSecret = apiSecret
        self.testnet = testnet

        self.client = Client(self.apiKey, self.apiSecret)                                                                             
        self.exchange = ccxt.binance({ 'apiKey': self.apiKey, 'secret': self.apiSecret})                                                              
        self.exchange.load_markets()



    def marketConfig(self, symbol: str, timeFrame: str):

        self.symbol = symbol.upper()
        self.timeFrame = timeFrame
        self.filename = 'market_data/'+self.symbol+'_'+timeFrame
        self.baseCurrency = self.symbol[:-4]
        self.quoteCurrency = self.symbol[-4:]
        self.baseAssetPrecision, self.quoteAssetPrecision, self.minNotional, self.tickSize = self.getPrecision()
        self.cacheData = pd.DataFrame()



    def loadData(self):

        try:

            timeFrame = self.timeFrame
            symbol = self.symbol

            filename = self.filename
            if not os.path.exists('market_data'):
                os.makedirs('market_data')

            bars = self.exchange.fetch_ohlcv(symbol, timeframe= timeFrame)
            data = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            data = data.iloc[:-1]
            rnd = len(str(data['close'].iloc[0]).split('.')[1])

            data.to_parquet(filename+'.gzip',compression='gzip')

            self.cacheData = data[['time', 'high', 'low', 'close']]

        except Exception as e:

            print("Error while loading data! | ", e)



    def getAcBalance(self, currencyType: str):

        try:

            if currencyType == 'base':
                currency = self.baseCurrency

            elif currencyType == 'quote':
                currency = self.quoteCurrency

            balance = self.client.get_asset_balance(asset= currency)

            return float(balance['free'])
        
        except Exception as e:

            print("Error while fetching balance! | ", e)

            return None




    def topup_bnb(self, min_balance: float, topup: float):

        try:

            # Top up BNB balance if it drops below minimum specified balance
            bnb_balance = self.client.get_asset_balance(asset='BNB')
            bnb_balance = float(bnb_balance['free'])

            if bnb_balance < min_balance:
                qty = round(topup - bnb_balance, 5)
                print(qty)
                order = self.client.order_market_buy(symbol='BNBUSDT', quantity=qty)

                return order

            return False

        except Exception as e:

            print("Error while top-upping BNB! | ", e)




    def getPrecision(self):
        baseAssetPrecision = 0
        quoteAssetPrecision = 0
        minNotional = 0
        tickSize = 0
        try:

            exchangeinfo = self.client.get_exchange_info()

            for sm in exchangeinfo['symbols']:

                if(sm['symbol'] == self.symbol):
                    
                    for filter in sm['filters']:

                        if(filter['filterType']=='LOT_SIZE'):

                            baseAssetPrecision = filter['stepSize']

                        elif(filter['filterType']=='PRICE_FILTER'):

                            quoteAssetPrecision = filter['minPrice']
                            tickSize = filter['tickSize']

                        elif(filter['filterType']=='MIN_NOTIONAL'):

                            minNotional = filter['minNotional']

            return baseAssetPrecision, quoteAssetPrecision, minNotional, tickSize        

        except Exception as e:

            print("Error while fetching price precision! | ", e)

            return None




    def truncateToPrecision(self, value: str, ndigits: int):

        try:

            if 'e' in value:
                value = "{:.{}f}".format(float(value), ndigits)
            else:
                integerPart,decimalPart = value.split('.')
                value = integerPart+'.'+decimalPart[:ndigits]

            return value

        except Exception as e:

            print('Error in truncating! | ', e)




    def precisionTrim(self, value: str):

        p0, p1 = value.split('.')

        if(p0=='0'):
            p = p1.split('1')[0]
            return (len(p)+1), 'flt'

        else:
            return (int(p0)), 'int'
        



    def placeMarketOrder(self, side: str, quantity: float, type='MARKET'):

        try:

            if side=='SELL':

                precision, pos = self.precisionTrim(self.baseAssetPrecision)

                if pos == 'int':
                    quantity = int(quantity)
                else:
                    quantity = self.truncateToPrecision(value = str(quantity), ndigits = precision)

                try:
                    testorder = self.client.create_test_order(  symbol = self.symbol, 
                                                side = 'SELL',
                                                type = type.upper(),
                                                quantity = float(quantity), 
                                                newOrderRespType ="FULL")
                
                except Exception as e:
                    print(e)
            
                if testorder=={}:
                    order = self.client.create_order(symbol = self.symbol, 
                                                    side = 'SELL',
                                                    type = type.upper(),
                                                    quantity = float(quantity), 
                                                    newOrderRespType ="FULL")

            
            
            elif side=='BUY':

                precision, pos = self.precisionTrim(self.quoteAssetPrecision)

                if pos == 'int':
                    quantity = int(quantity)
                else:
                    quantity = self.truncateToPrecision(value = str(quantity), ndigits = precision)

                try:
                    testorder = self.client.create_test_order(  symbol = self.symbol, 
                                                side = 'BUY',
                                                type = type.upper(),
                                                quantity = float(quantity), 
                                                newOrderRespType ="FULL")
                except Exception as e:
                    print(e)
                
                if testorder=={}:
                    order = self.client.create_order(symbol = self.symbol, 
                                                    side = 'BUY',
                                                    type = type.upper(),
                                                    quantity = float(quantity), 
                                                    newOrderRespType ="FULL")


            return order

        except BinanceAPIException as e:
            # error handling goes here
            print(e)

            return None

        except BinanceOrderException as e:
            # error handling goes here
            print(e)

            return None




    def updateData(self, data, cachesize= 700):

        try:

            data0 = pd.read_parquet(self.filename+'.gzip')

            new_row = pd.DataFrame([{ 'time':data['t'], 
                        'open':float(data['o']), 
                        'high':float(data['h']), 
                        'low':float(data['l']), 
                        'close':float(data['c']), 
                        'volume':float(data['v'])
                    }])

            data0 = pd.concat([data0, new_row], ignore_index=True)

            self.cacheData = data0[['time', 'high', 'low', 'close']]

            data0.to_parquet(self.filename+'.gzip', compression='gzip')

        except Exception as e:

            print("Error while updating data! | ", e)




class exchangeStream():

    def __init__(self, symbol: str, timeframe: str, exchange: cryptoExchange):
    
        # __init__(self, symbol: str, timeframe: str): This is the constructor method which gets called when an object of this class is created. 
        # It initializes the following variables -

        #   `stop_event: This is an event object which is used to stop the thread`
        #   `symbol: This variable holds the symbol passed to the class object at the time of its creation`
        #   `timeframe: This variable holds the timeframe passed to the class object at the time of its creation`
        #   `indicator: This is an object of the indicators class`
        #   `trade: This is an object of the tradeStrategy class`

        self.stop_event = threading.Event()
        self.symbol = symbol.lower()
        self.timeframe = timeframe
        self.indicator = indicators()
        self.tradestrategy = tradeStrategy(exchange)
        self.exchange = exchange


    def on_open(self, ws):

        # on_open(self, ws): This method gets called when a websocket connection is opened. 
        # It prints the current time and date to the console.

        stime = datetime.now()
        start_time = stime.strftime("%b-%d-%Y %H:%M:%S")
        print(f"Opened connection : {start_time}")


    def on_message(self, ws, message):

        # on_message(self, ws, message): This method gets called when a message is received on the websocket connection. 
        # It parses the received message, which is in json format, and updates the exchange.cacheData with it. 
        # Then it calls the trade_signal_indicator method of indicator object, which returns a signal, 'buy' or 'sell', based on the current price and the indicators. 
        # If the signal is 'buy', it calls the buy method of trade object and if it is 'sell', it calls the sell method of trade object.

        try:
            json_message = json.loads(message)
            time = int(json_message["E"])
            candle = json_message['k']
            price = float(candle['c'])
            tframe = candle['i']
            is_candle_closed = candle['x']

            if is_candle_closed:

                self.exchange.updateData(candle)

                t, p, signal = self.indicator.trade_signal_indicator(self.exchange.cacheData, tframe)


                if signal == 'buy':

                    self.tradestrategy.buy(price, time)


                elif signal == 'sell':

                    self.tradestrategy.sell(price, time)
        
        except Exception as e:

            print("Error on message! | ", e)


    def on_close(self, ws):

        # on_close(self, ws): This method gets called when a websocket connection is closed.

        print('Closed connection')
    

    def socketConnect(self):

        # _socketConnect(self): This method creates a new websocket connection and runs it forever. 
        # It checks if the stop_event is set in every iteration of the loop, if it is, it stops running the websocket connection.

        url = "wss://stream.binance.com:9443/ws/"+self.symbol.lower()+"@kline_"+self.timeframe                                                                                                                                                                     #
                                          
        while not self.stop_event.is_set():
            ws = websocket.WebSocketApp(url, on_open=self.on_open, 
                                        on_close=self.on_close, 
                                        on_message=self.on_message)

            ws.run_forever()

    
    def stop(self):

        # stop(self): This method sets the stop_event so that the thread running the _socketConnect method stops running.

        self.stop_event.set()




'''
bal = ex.getAcBalance('quote')
print(bal)
print(ex.baseAssetPrecision, ex.quoteAssetPrecision)
print(ex.placeMarketOrder('BUY', bal))


bal = ex.getAcBalance('base')
print(bal)
print(ex.baseAssetPrecision, ex.quoteAssetPrecision)
print(ex.placeMarketOrder('SELL', bal))
'''