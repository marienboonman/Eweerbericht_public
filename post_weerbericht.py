import pandas as pd
import datetime
import keys as tokens
import tweepy
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots
pio.renderers.default='browser'
import kaleido
import os
import get_data as get
import sys

path = ''
if 'win' in sys.platform:
    try:
        p = os.path.abspath(__file__).split('\\')
        path = '{}/'.format('/'.join(p[0:len(p)-1]))
        print('windows '+path)
        os.chdir(path)
    except:
        print('running from spyder, working folder is {}'.format(os.getcwd()))


if 'linux' in sys.platform:
    try:
        p = os.path.abspath(__file__).split('/')
        path = '{}/'.format('/'.join(p[0:len(p)-1]))
        print('linux '+path)
        os.chdir(path)
    except:
        print('running from spyder, working folder is {}'.format(os.getcwd()))


delivery_date = datetime.date.today()+datetime.timedelta(days = 1)

## DATA OPHALEN

# Day ahead prijzen van de ENTSOE API halen en NL belasting toepassen
prices = get.prices_api(delivery_date = delivery_date)/1000
pricesincl = round((prices+0.1525/1.21+0.025)*1.21,4) #2.5 cent terugleververgoeding obv Allinpower

# forecast van hernieuwbare opwek ophalen
renewableforecast = get.renewable_forecast_api(delivery_date = delivery_date)

# forecast van totale elektriciteitsvraag
l = get.load_forecast_api(delivery_date = delivery_date)
loadforecast = pd.Series(index = l.index, dtype = float)
for i in l.index:
    loadforecast[i] = l.loc[i]


loadforecast = loadforecast/1000
renewableforecast = renewableforecast/1000
restlast = loadforecast - renewableforecast.sum(axis = 1)


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
mean = prices-prices+mean

# sorteren om duurste uur te vinden
sort = pricesincl.sort_values(ascending = False)
duursteuur = "€"+str(round(sort.iloc[0],3))
time = '{}-{}'.format(sort.index[0].strftime('%H:%M'),(sort.index[0]+datetime.timedelta(hours=1)).strftime('%H:%M'))
duurste = '{}: {}'.format(time,duursteuur)

# sorteren om goedkoopste uur te vinden
sort = pricesincl.sort_values()
goedkoopsteuur = "€"+str(round(sort.iloc[0],3))
time = '{}-{}'.format(sort.index[0].strftime('%H:%M'),(sort.index[0]+datetime.timedelta(hours=1)).strftime('%H:%M'))
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
ochtend = s[range(9)].sort_values()
middag = s[range(11,17)].sort_values()
avond =  s[range(17,23)].sort_values()

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
    time = vec.index[0]
    prijs = round(vec[time],3)
    strs.append('{}-{}: €{}'.format(time.strftime('%H:%M'),(time+datetime.timedelta(hours=+delta)).strftime('%H:%M'),prijs))

tweet = "Prijscurve voor morgen!\nDuurste uur:\n{}\nGoedkoopste uur:\n{}\nGoedkoopste aaneengesloten uren:\n\
hele dag:   {}\n\'s Morgens: {}\n\'s Middags: {}\n\'s Avonds:  {}" \
        .format(duurste,goedkoopste,strs[0],strs[1],strs[2],strs[3])

print(tweet)

# maak strings van indexen voor plotten
for s in [prices, pricesincl, renewableforecast, loadforecast]:
    s.index = s.index.strftime('%H:%M')

## START API
auth = tweepy.OAuthHandler(tokens.APIKey, tokens.APISecret)
auth.set_access_token(tokens.AccessToken, tokens.AccessSecret)
api = tweepy.API(auth)
imgs = []

# plot prijs, prijsincl en modelcontract
fig = go.Figure()
fig.add_trace(go.Scatter(
    name="Kaal",
    mode="lines", x=prices.index, y=prices,
    line = {"shape":"hv"}))
fig.add_trace(go.Scatter(
    name="All-in",
    mode="lines", x=pricesincl.index, y=pricesincl,
    line = {"shape":"hv"}))
fig.add_trace(go.Scatter(
    name="Modelcontract",
    mode="lines", x=pricesincl.index, y=mean,
    line = {"shape":"hv"}))
fig.update_layout(
    title="Elektriciteitsprijs (€/kWh) "+ delivery_date.strftime("%d-%m-%Y"),
    xaxis_title="Tijd")

fig.update_yaxes(title_text="Prijs (€/kWh)")
fig.update_xaxes(dtick = 2, tickangle = 45)

if min(prices)>0:
    fig.update_yaxes(rangemode="tozero")

filename = 'prijscurve_'+delivery_date.strftime('%d%m%Y')+'.png'

fig.write_image(filename)

media = api.media_upload(filename)
imgs.append(media.media_id_string)
os.remove(filename)

# plot renewable forecast
fig = go.Figure()
fig.add_trace(go.Scatter(
    name="Totale vraag",
    mode="lines", x=loadforecast.index, y=loadforecast,
    line = {"shape":"spline", 'smoothing':1.3}))
fig.add_trace(go.Scatter(
    name="Wind op zee",
    x=renewableforecast.index, y=renewableforecast['Wind Offshore'],
    stackgroup='one', fillcolor = 'aqua', line_color='aqua'))
fig.add_trace(go.Scatter(
    name="Wind op land",
    x=renewableforecast.index, y=renewableforecast['Wind Onshore'],
    stackgroup='one',fillcolor = 'mediumaquamarine', line_color='mediumaquamarine'))
fig.add_trace(go.Scatter(
    name="Zon",
    x=renewableforecast.index, y=renewableforecast['Solar'],
    stackgroup='one',fillcolor = 'goldenrod', line_color='goldenrod'))
fig.update_layout(
    title="Voorspelling zon en wind en totale vraag (GW) "+ delivery_date.strftime("%d-%m-%Y"),
    xaxis_title="Tijd")

fig.update_yaxes(title_text="GW")
fig.update_xaxes(dtick = 8, tickangle = 45)
fig.update_yaxes(rangemode="tozero")


filename = 'figs/forecast_'+delivery_date.strftime('%d%m%Y')+'.png'


fig.write_image(filename)

media = api.media_upload(filename)
imgs.append(media.media_id_string)
#os.remove(filename)


# Create figure with secondary y-axis
fig = make_subplots(specs=[[{"secondary_y": True}]])
fig.add_trace(go.Scatter(
    name="Restlast",
    mode="lines", x=loadforecast.index, y= restlast,
    line = {"shape":"spline", 'smoothing':1.3}), secondary_y = True)
fig.add_trace(go.Scatter(
    name="All-in prijs",
    mode="lines", x=pricesincl.index, y=pricesincl,
    line = {"shape":"hv"}), secondary_y = False)
'''
fig.add_trace(go.Scatter(
    name="Modelcontract",
    mode="lines", x=pricesincl.index, y=mean,
    line = {"shape":"hv"}))
'''
fig.update_layout(
    title="Elektriciteitsprijs en restlast "+ delivery_date.strftime("%d-%m-%Y"),
    xaxis_title="Tijd")
fig.update_xaxes(dtick = 8, tickangle = 45)
fig.update_yaxes(title_text="Prijs (€/kWh)", secondary_y=False)
fig.update_yaxes(title_text="Restlast (GW)", secondary_y=True)


##TODO ALIGN Y AXES
if min(prices)>0 and min(loadforecast - renewableforecast.sum(axis = 1))>0:
    #bepaal lengte van beide assen
    tprices = round(max(pricesincl)*1.1,1)
    trestlast = round(max(restlast)*1.1+0.49,0)
    fig.update_layout(yaxis = dict(range = [0,tprices], dtick = tprices/10), yaxis2 = dict(range = [0,trestlast],dtick = trestlast/10))

filename = 'residualload_'+delivery_date.strftime('%d%m%Y')+'.png'

fig.write_image(filename)


## Figuur met restlast, prijs, forecasts.
'''
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

'''


media = api.media_upload(filename)
imgs.append(media.media_id_string)
os.remove(filename)

client = tweepy.Client(consumer_key=tokens.APIKey,
                       consumer_secret=tokens.APISecret,
                       access_token=tokens.AccessToken,
                       access_token_secret=tokens.AccessSecret)

client.create_tweet(text = tweet, media_ids = imgs)
