import pandas as pd
from entsoe import EntsoePandasClient
import datetime
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default='browser'
import kaleido
import os
import keys
from plotly.subplots import make_subplots

def prices_api(country = 'NL', delivery_date = datetime.date.today()+datetime.timedelta(days = 1)):
    client = EntsoePandasClient(api_key=keys.entsoe_api_key)
    
    start = pd.Timestamp(delivery_date, tz='Europe/Brussels')
    end = start+datetime.timedelta(hours = 24)

    prices = client.query_day_ahead_prices(country, start = start, end = end)
    prices.name = 'Prijs (€/MWh), {}'.format(delivery_date)
    return prices

def renewable_forecast_api(country = 'NL', delivery_date = datetime.date.today()+datetime.timedelta(days = 1)):
    client = EntsoePandasClient(api_key=keys.entsoe_api_key)
    
    start = pd.Timestamp(delivery_date, tz='Europe/Brussels')
    end = start+datetime.timedelta(hours = 24)
    
    forecast = client.query_wind_and_solar_forecast(country, start = start, end = end)
    forecast.name = 'Generation forecast, {}'.format(delivery_date)
    return forecast #.resample('H').mean()
    

def load_forecast_api(country = 'NL', delivery_date = datetime.date.today()+datetime.timedelta(days = 1)):
    client = EntsoePandasClient(api_key=keys.entsoe_api_key)
    
    start = pd.Timestamp(delivery_date, tz='Europe/Brussels')
    end = start+datetime.timedelta(hours = 24)
    
    forecast = client.query_load_forecast(country, start = start, end = end)
    forecast.name = 'Generation forecast, {}'.format(delivery_date)
    return forecast #.resample('H').mean()

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

def modelcontract(data):
    series = pd.Series(index = data.index, data = 0)
    #prijs van het modelcontract ophalen
    url = 'https://www.overstappen.nl/energie/energietarieven/#Overzicht_energietarieven_2022'
    table = pd.read_html(url)[0]
    
    enkeltarieven = []
    for i in table.index:
        try:
            tarief = float(table['Enkeltarief'][i].strip('€').replace(',','.'))
            enkeltarieven.append(tarief)
        except:
            print('Tarief NA')    
    
    mean = sum(enkeltarieven)/len(enkeltarieven)
    mean = series-series+mean
    return mean

def write_tweet(forecasts, land):
    def hourfromint(i):
        if i <10:
            return '{}{}:00'.format(0,i)
        else:
            return'{}:00'.format(i)
            
    pricesincl = pd.Series(forecasts['Pricesincl']).iloc[::4]
    # sorteren om duurste uur te vinden
    sort = pricesincl.sort_values(ascending = False)
    uur = int(sort.index[0][:2])
    duursteuur = "€"+str(round(sort.iloc[0],3))
    time = '{}-{}'.format(hourfromint(uur), hourfromint(uur+1))
    duurste = '{}: {}'.format(time,duursteuur)
    
    # sorteren om goedkoopste uur te vinden
    sort = pricesincl.sort_values()
    goedkoopsteuur = "€"+str(round(sort.iloc[0],3))
    uur = int(sort.index[0][:2])
    time = '{}-{}'.format(hourfromint(uur), hourfromint(uur+1))
    goedkoopste = '{}: {}'.format(time,goedkoopsteuur)
    
    # lege serie om voortschrijdende gemiddelden in te maken (2hr)
    s = pd.Series(index = pricesincl.index, dtype = float)
    
    # 2hr voortschrijdend gemiddelde bepalen
    for i in range(len(s.index)-1):
      s.iloc[i] = (pricesincl.iloc[i]+pricesincl.iloc[i+1])/2
    '''
    # eerste uur verwijderen, want geen 2hr voortschrijdend gemiddelde
    s = s.drop(s.index[0])
    '''
    
    # goedkoopste intervallen selecteren INDEX = BEGINTIJD
    ochtend = s[:12].sort_values()
    middag = s[11:17].sort_values()
    avond =  s[18:].sort_values()
    
    # lege serie voor 3hr voortschrijdend gemiddelde
    s2 = pd.Series(index = pricesincl.index, dtype = float)
    
    # 3hr voortschrijdend gemiddelde bepalen
    for i in range(len(s2.index)-2):
      s2.iloc[i] = (pricesincl.iloc[i]+pricesincl.iloc[i+1]+pricesincl.iloc[i+2])/3
    '''
    # eerste 2 uur verwijderen want geen 3hr voortschrijdend gemiddelde
    s = s.drop(s.index[0:1])
    '''
    dag = s2.sort_values() #index = begintijd
    strs = []
    
    for vec, delta in zip([dag, ochtend, middag, avond],[3,2,2,2]):
        uur = int(vec.index[0][:2])
        prijs = round(vec[vec.index[0]],3)
        strs.append('{}-{}: €{}'.format(hourfromint(uur),hourfromint(uur+delta),prijs))
    
    tweet = "Prijzen morgen ({})!\nDuurste uur:\n{}\nGoedkoopste uur:\n{}\nGoedkoopste aaneengesloten uren:\n\
    hele dag:   {}\n\'s Morgens: {}\n\'s Middags: {}\n\'s Avonds:  {}\n\n {}grafiekvandedag" \
            .format(land, duurste,goedkoopste,strs[0],strs[1],strs[2],strs[3],"#")
    
    return tweet

def plot_prices(forecasts, landnaam, delivery_date):
        # plot prijs, prijsincl en modelcontract
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        name="Kaal",
        mode="lines", x=forecasts.index, y=forecasts['Prices'],
        line = {"shape":"hv"}))
    fig.add_trace(go.Scatter(
        name="All-in",
        mode="lines", x=forecasts.index, y=forecasts['Pricesincl'],
        line = {"shape":"hv"}))
    fig.add_trace(go.Scatter(
        name="Modelcontract (NL)",
        mode="lines", x=forecasts.index, y=forecasts['Modelcontract'],
        line = {"shape":"hv"}))
    fig.update_layout(
        title="Elektriciteitsprijs "+landnaam+" (€/kWh) "+ delivery_date.strftime("%d-%m-%Y"),
        xaxis_title="Tijd")
    
    fig.update_yaxes(title_text="Prijs (€/kWh)")
    fig.update_xaxes(dtick = 8, tickangle = 45)
    
    #kleuren
    fig.update_layout(plot_bgcolor='#FFFFFF')
    fig.update_layout(paper_bgcolor='rgb(220,230,242)')
    fig.update_yaxes(showline=True, gridcolor = 'lightgrey')
    fig.update_layout(title_x = 0.5)
    #note linksonder
    fig.add_annotation(text='Eweerbericht/Overstappen.com/ENTSO-E', 
                    align='left',
                    showarrow=False,
                    xref='paper',
                    yref='paper',
                    x=-0.17,
                    y=-0.25)
    
    
    if min(forecasts['Prices'])>0:
        fig.update_yaxes(rangemode="tozero")
    return fig

def plot_forecasts(forecasts, landnaam, delivery_date):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        name="Wind op zee",
        x=forecasts.index, y=forecasts['Wind Offshore'],
        stackgroup='one', fillcolor = 'aqua', line_color='aqua'))
    fig.add_trace(go.Scatter(
        name="Wind op land",
        x=forecasts.index, y=forecasts['Wind Onshore'],
        stackgroup='one',fillcolor = 'mediumaquamarine', line_color='mediumaquamarine'))
    fig.add_trace(go.Scatter(
        name="Zon",
        x=forecasts.index, y=forecasts['Solar'],
        stackgroup='one',fillcolor = 'goldenrod', line_color='goldenrod'))
    
    fig.add_trace(go.Scatter(
            name="Totale vraag",
            mode="lines", x=forecasts.index, y=forecasts['Load'],
            line = {'color':'royalblue', "shape":"spline", 'smoothing':1.3}))
 
    fig.add_trace(go.Scatter(
            name="Totale vraag",
            mode="lines", x=forecasts.index, y=forecasts['Restlast'],
            line = {'color':'crimson', "shape":"spline", 'smoothing':1.3}))
    
    
    fig.update_layout(
        title="Voorspelling zon en wind en totale vraag "+landnaam+" (GW) "+ delivery_date.strftime("%d-%m-%Y"),
        xaxis_title="Tijd")
    
    fig.update_yaxes(title_text="GW")
    fig.update_xaxes(dtick = 8, tickangle = 45)
    fig.update_yaxes(rangemode="tozero")
    
    #kleuren
    fig.update_layout(plot_bgcolor='#FFFFFF')
    fig.update_layout(paper_bgcolor='rgb(220,230,242)')
    fig.update_yaxes(showline=True, gridcolor = 'lightgrey')
    fig.update_layout(title_x = 0.5)
    #note linksonder
    fig.add_annotation(text='Eweerbericht/Overstappen.com/ENTSO-E', 
        align='left',
        showarrow=False,
        xref='paper',
        yref='paper',
        x=-0.17,
        y=-0.25)
    
    return fig

def plot_loads(forecasts, landnaam, delivery_date):
    # Figuur met restlast en renewable forecast
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
            name="Restlast",
            mode="lines", x=forecasts.index, y= forecasts['Restlast'],
            line = {"shape":"spline", 'smoothing':1.3}), secondary_y = True)
    fig.add_trace(go.Scatter(
        name="All-in prijs",
        mode="lines", x=forecasts.index, y=forecasts['Pricesincl'],
        line = {"shape":"hv"}), secondary_y = False)
    '''
    fig.add_trace(go.Scatter(
        name="Modelcontract",
        mode="lines", x=pricesincl.index, y=mean,
        line = {"shape":"hv"}))
    '''
    fig.update_layout(
        title="Elektriciteitsprijs en restlast "+landnaam+ " "+ delivery_date.strftime("%d-%m-%Y"),
        xaxis_title="Tijd")
    fig.update_xaxes(dtick = 8, tickangle = 45)
    fig.update_yaxes(title_text="Prijs (€/kWh)", secondary_y=False)
    fig.update_yaxes(title_text="Restlast (GW)", secondary_y=True)
    
    
    ##TODO ALIGN Y AXES
    '''
    if min(prices)>0 and min(loadforecast - renewableforecast.sum(axis = 1))>0:
        #bepaal lengte van beide assen
        tprices = round(max(pricesincl)*1.1,1)
        trestlast = round(max(restlast)*1.1+0.49,0)
        fig.update_layout(yaxis = dict(range = [0,tprices], dtick = tprices/10), yaxis2 = dict(range = [0,trestlast],dtick = trestlast/10))
    '''
    #kleuren
    fig.update_layout(plot_bgcolor='#FFFFFF')
    fig.update_layout(paper_bgcolor='rgb(220,230,242)')
    fig.update_yaxes(showline=True, gridcolor = 'lightgrey')
    fig.update_layout(title_x = 0.5)
    #note linksonder
    fig.add_annotation(text='Eweerbericht/Overstappen.com/ENTSO-E', 
                    align='left',
                    showarrow=False,
                    xref='paper',
                    yref='paper',
                    x=-0.17,
                    y=-0.25)
    return fig  


'''

def subplots():
    ## Figuur met restlast, prijs, forecasts.   
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        name="Totale vraag",
        mode="lines", x=loadforecast.index, y=loadforecast,
        line = {"shape":"spline", 'smoothing':1.3}), secondary_y = True)
    fig.add_trace(go.Scatter(
        name="Wind op zee",
        x=renewableforecast.index, y=renewableforecast['Wind Offshore'],
        stackgroup='one', fillcolor = 'aqua', line_color='aqua'), secondary_y = True)
    fig.add_trace(go.Scatter(
        name="Wind op land",
        x=renewableforecast.index, y=renewableforecast['Wind Onshore'],
        stackgroup='one',fillcolor = 'mediumaquamarine', line_color='mediumaquamarine'), secondary_y = True)
    fig.add_trace(go.Scatter(
        name="Zon",
        x=renewableforecast.index, y=renewableforecast['Solar'],
        stackgroup='one',fillcolor = 'goldenrod', line_color='goldenrod'), secondary_y = True)
    fig.update_layout(
        title="Voorspelling zon en wind en totale vraag (GW) "+ delivery_date.strftime("%d-%m-%Y"),
        xaxis_title="Tijd")
    fig.add_trace(go.Scatter(
        name="Restlast",
        mode="lines", x=loadforecast.index, y= restlast,
        line = {"shape":"spline", 'smoothing':1.3}), secondary_y = True)
    fig.add_trace(go.Scatter(
        name="All-in prijs",
        mode="lines", x=pricesincl.index, y=pricesincl,
        line = {"shape":"hv"}), secondary_y = False)
    fig.update_xaxes(dtick = 8, tickangle = 45)
    if min(pricesincl)>0 and min(loadforecast)>0:
        #bepaal lengte van beide assen
        tprices = round(max(pricesincl)*1.1,1)
        trestlast = round(max(loadforecast)*1.1+0.49,0)
        fig.update_layout(yaxis = dict(range = [0,tprices], dtick = tprices/10), yaxis2 = dict(range = [0,trestlast],dtick = trestlast/10))
    return fig
'''


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
