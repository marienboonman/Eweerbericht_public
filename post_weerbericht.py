import pandas as pd
import datetime
import keys as tokens
import tweepy
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default='browser'
import kaleido
import os
import get_data as get

delivery_date = datetime.date.today()+datetime.timedelta(days=1)
## DATA OPHALEN

# Day ahead prijzen van de ENTSOE API halen en NL belasting toepassen
prices = get.prices_api()
pricesincl = round((prices+0.03679+0.0305)*1.09,4)

# forecast van hernieuwbare opwek ophalen
renewableforecast = get.renewable_forecast_api()
loadforecast = get.load_forecast_api()

#prijs van het modelcontract ophalen
url = 'https://www.overstappen.nl/energie/energietarieven/#Overzicht_energietarieven_2022'
table = pd.read_html(url)[0]
table.columns = table.iloc[0]
table = table.drop(0, axis = 0)
try:
    mean = pd.Series(table[table.columns[3]]).str.strip('€').str.replace(',','.').astype(float).mean()
except:
    mean = pd.Series(table[table.columns[1]]).str.strip('€').str.replace(',','.').astype(float).mean()
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
for i in range(1,len(s.index)):
  s.iloc[i] = pricesincl.iloc[i-1:i+1].mean()

# eerste uur verwijderen, want geen 2hr voortschrijdend gemiddelde
s = s.drop(s.index[0])

# goedkoopste intervallen selecteren
ochtend = s[range(1,8)].sort_values()
middag = s[range(8,16)].sort_values()
avond =  s[range(17,23)].sort_values()

# lege serie voor 3hr voortschrijdend gemiddelde
s = pd.Series(index = pricesincl.index, dtype = float)

# 3hr voortschrijdend gemiddelde bepalen
for i in range(2,len(s.index)):
  s.iloc[i] = pricesincl.iloc[i-2:i+1].mean()

# eerste 2 uur verwijderen want geen 3hr voortschrijdend gemiddelde
s = s.drop(s.index[0:1])

dag = s.sort_values()
strs = []

for vec, delta in zip([dag, ochtend, middag, avond],[2,2,2,3]):
    time = vec.index[0]
    prijs = round(vec[time],3)
    strs.append('{}-{}: €{}'.format(time.strftime('%H:%M'),(time+datetime.timedelta(hours=delta)).strftime('%H:%M'),prijs))

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
    line = {"shape":"hv"}))
fig.add_trace(go.Scatter(
    name="Wind op zee",
    x=renewableforecast.index, y=renewableforecast['Wind Offshore'],
    stackgroup='one', fillcolor = 'green'))
fig.add_trace(go.Scatter(
    name="Wind op land",
    x=renewableforecast.index, y=renewableforecast['Wind Onshore'],
    stackgroup='one',fillcolor = 'blue'))
fig.add_trace(go.Scatter(
    name="Zon",
    x=renewableforecast.index, y=renewableforecast['Solar'],
    stackgroup='one',fillcolor = 'yellow'))
fig.update_layout(
    title="Voorspelling zon en wind en totale vraag (MW) "+ delivery_date.strftime("%d-%m-%Y"),
    xaxis_title="Tijd")
fig.update_xaxes(dtick = 2, tickangle = 45)
fig.update_yaxes(rangemode="tozero")

fig.update_layout(yaxis_range=[0, max(max(loadforecast.values[0]),max(renewableforecast.sum(axis=1)))])

filename = 'forecast_'+delivery_date.strftime('%d%m%Y')+'.png'

fig.write_image(filename)

media = api.media_upload(filename)
imgs.append(media.media_id_string)
os.remove(filename)


client = tweepy.Client(consumer_key=tokens.APIKey,
                       consumer_secret=tokens.APISecret,
                       access_token=tokens.AccessToken,
                       access_token_secret=tokens.AccessSecret)

client.create_tweet(text = tweet, media_ids = imgs)
