import config
import pandas as pd
import pandas_ta as ta
from ta.volatility import AverageTrueRange
import dash
from dash.dependencies import Output, Input
from dash import dcc
from dash import html
import plotly
import config
import plotly.graph_objs as go
from collections import deque
import pandas as pd
global i, df

def supertrend(dm, period=100, atr_multiplier=3):
    try:
        d=ta.supertrend(dm['high'], dm['low'], dm['close'], length=period, multiplier=atr_multiplier)
        return d[d.columns[0]]
    except Exception as e:
        print('Error in supertrend',e)

def analyse(symbol, timeframe):
    #global signal_data, asset_data, inPosition, trend_signal_data
    try:
        _filename = '_market_data_csv/'+symbol+'_'+timeframe
        d = pd.read_parquet(_filename+'.gzip')
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
        
        if timeframe==config.timeFrame_main:            
            dm['in_uptrend'] = supertrend(dm, period=100, atr_multiplier=3.46)
        else:
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
            atr = AverageTrueRange(dm['high'],dm['low'],dm['close'],window=config.atrtrailing_length)
            dm['atr2'] = atr.average_true_range()
            dm['stoploss'] = dm['close']-(config.atrStoploss*dm['atr'])
            dm['takeprofit'] = dm['close']+(config.atrTakeprofit*dm['atr'])
        return dm

    except Exception as e:
        print('Error in analyse',e)

i=-40
df = analyse(config.symbol,config.timeFrame)
t = df['time'].iloc[i]
X = deque(maxlen = 40)
X.append(t)

p = df['close'].iloc[i]
Y = deque(maxlen = 40)
Y.append(p)
  
app = dash.Dash(__name__)
  
app.layout = html.Div(
    [
        html.Div([
            html.H2(config.symbol),
            html.H5(),
        ]),

        dcc.Graph(id = 'live-graph', animate = True),
        dcc.Interval(
            id = 'graph-update',
            interval = 1000,
            n_intervals = 0
        ),
    ]
)
  
@app.callback(
    Output('live-graph', 'figure'),
    [ Input('graph-update', 'n_intervals') ]
) 
def update_graph_scatter(n):
    global i
    df = analyse(config.symbol,config.timeFrame)
    if i<-1:
        X.append(df['time'].iloc[i])
        Y.append(df['close'].iloc[i])
        i=i+1
    else:
        if(df['time'].iloc[i]!=X[-1]):
            X.append(df['time'].iloc[i])
            Y.append(df['close'].iloc[i])

    data = plotly.graph_objs.Scatter(
            x=list(X),
            y=list(Y),
            name='Scatter',
            mode= 'lines+markers'
    )
    return {'data': [data],
            'layout' : go.Layout(xaxis=dict(range=[min(X),max(X)]),yaxis = dict(range = [min(Y),max(Y)]),)}
  
if __name__ == '__main__':
    app.run_server()
