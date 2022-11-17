import pandas as pd
from entsoe import EntsoePandasClient
import datetime
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default='browser'
import kaleido
import os

def get_prices(api_key, start, end, country_code = 'NL'):
    client = EntsoePandasClient(api_key=api_key)
    
    #start = pd.Timestamp(datetime.date.today()+datetime.timedelta(days = 1), tz='Europe/Brussels')
    #end = start+datetime.timedelta(hours = 23)
       
    # methods that return XML
    prices = client.query_day_ahead_prices(country_code, start = start, end = end)
    return prices

def plot_prices(prices, startdate, save = True):
    prices.index = pd.date_range(start = '00:00', freq = 'H', periods = len(prices)).strftime("%H:%M")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Elektriciteitsprijs (€/MWh) "+ startdate.strftime("%d-%m-%Y"),
        mode="lines+markers", x=prices.index, y=prices,
        marker_symbol="square", line= {"shape": 'hv'}))

    fig.update_layout(
        title="Elektriciteitsprijs (€/MWh) "+ startdate.strftime("%d-%m-%Y"),
        xaxis_title="Tijd")
    
    if save:
        filename = 'figs/prijscurve '+startdate.strftime('%d%m%Y')+'.jpg'
        if os.path.isfile(filename):
           overwrite = input(filename + " is already there, overwrite? (Y/N)")
           if overwrite:
               fig.write_image(filename)
        else:
            fig.write_image(filename)


def findpeaks(s):
    p = []
    for i in range(1, len(s)-1):
        if s[i-1]<s[i] and s[i+1]<s[i]:
            p.append(i)
    return p

def findbots(s):
    b = []
    for i in range(1, len(s)-1):
        if s[i-1]>s[i] and s[i+1]>s[i]:
            b.append(i)
    return b

def deapestbots(s, b, p):
    if b[0] > p[0]:
        
        return b

def highestpeaks():

    return p
def findtwopeaks(series):
    return series
