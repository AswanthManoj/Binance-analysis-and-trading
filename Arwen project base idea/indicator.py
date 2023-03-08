import pandas as pd
import numpy as np


class indicators():

    def __init__(self):
        pass


    def macd(self, data, fastLength=12, slowLength=26, signalSmoothing=9):

        # Create the fast and slow exponential moving averages (EMAs)
        data["ema_fast"] = data["close"].ewm(span=fastLength, adjust=False).mean()
        data["ema_slow"] = data["close"].ewm(span=slowLength, adjust=False).mean()

        # Create the MACD line
        data["macd"] = data["ema_fast"] - data["ema_slow"]

        # Create the signal line
        data["signal"] = data["macd"].ewm(span=signalSmoothing, adjust=False).mean()

        # Create the histogram
        data["histogram"] = data["macd"] - data["signal"]

        return data




    def average_true_range(self, data, length=12):
        
        # Create the True Range column
        data["tr"] = data[["high", "low", "close"]].apply(lambda x: max(x) - min(x), axis=1)

        # Create the ATR column using the EMA with length
        data["atr"] = data["tr"].rolling(window=length).mean()

        return data




    def buy_indicator(self, data, length=10, multiplier=1.25, atrAvgLength=12, baselineLength=600, return_data='histogram'):

        if 'atrn' not in data.columns:
            data = self.average_true_range(data)
        if 'signal' not in data.columns:
            data = self.macd(data)

        # Create the ATR column using EMA
        data["atrn"] = data['tr'].rolling(window=length).mean()*(-1*multiplier)

        # Create average ATR column
        data["atr_avg"] = data["atrn"].ewm(span=atrAvgLength, adjust=True).mean()

        # Create histogram
        data["b_histogram"] = data["signal"]-data["atr_avg"]

        # Create Baseline
        data["b_baseline"] = data["b_histogram"].rolling(window=baselineLength).mean()*(-1)

    
        if return_data == 'histogram':
            return data["b_histogram"]

        elif return_data == 'all':
            return data
            

        

    def sell_indicator(self, data, length=10, multiplier=1.25, atrAvgLength=12, baselineLength=600, return_data='histogram'):

        if 'atrn' not in data.columns:
            data = self.average_true_range(data)
        if 'signal' not in data.columns:
            data = self.macd(data)

        # Create the ATR column using EMA
        data["atrn"] = data['tr'].rolling(window=length).mean()*(multiplier)

        # Create average ATR column
        data["atr_avg"] = data["atrn"].ewm(span=atrAvgLength, adjust=True).mean()

        # Create histogram
        data["s_histogram"] = data["signal"]-data["atr_avg"]

        # Create Baseline
        data["s_baseline"] = data["s_histogram"].rolling(window=baselineLength).mean()*(-1)



        if return_data == 'histogram':
            return data["s_histogram"]

        elif return_data == 'all':
            return data


    

    def trade_signal_indicator(self, data, tframe='1m'):

        data = self.average_true_range(data)
        data = self.macd(data)
        bdata = self.buy_indicator(data, return_data='all')
        sdata = self.sell_indicator(data,  return_data='all')
        b_histogram = bdata["b_histogram"]
        b_baseline = bdata["b_baseline"]
        s_histogram = sdata["s_histogram"]
        s_baseline = sdata["s_baseline"]
        intervals = ['1m', '3m', '5m']
        action = "wait"

        # Check if histogram values are negative and if the histogram is increasing
        if (b_histogram.iloc[-3] < 0) and (b_histogram.iloc[-2] < 0) and (b_histogram.iloc[-1] < 0) and (b_histogram.iloc[-3] > b_histogram.iloc[-2]) and (b_histogram.iloc[-2] < b_histogram.iloc[-1]):
            if tframe in intervals:
                if b_histogram.iloc[-1]>b_baseline[-1]:
                    action = "buy"
            else:
                action = "buy"

        # Check if histogram values are positive and if the histogram is decreasing
        elif (s_histogram.iloc[-3] > 0) and (s_histogram.iloc[-2] > 0) and (s_histogram.iloc[-1] > 0) and (s_histogram.iloc[-3] < s_histogram.iloc[-2]) and (s_histogram.iloc[-2] > s_histogram.iloc[-1]):
            if tframe in intervals:
                if s_histogram.iloc[-1]<s_baseline[-1]:
                    action = "sell"
            else:
                action = "sell"


        return data['time'].iloc[-1], data['close'].iloc[-1], action