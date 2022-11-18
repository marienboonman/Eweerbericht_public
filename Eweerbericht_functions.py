import pandas as pd
import datetime
import keys as tokens
import tweepy
import plotly.graph_objects as go
import plotly.io as pio
pio.renderers.default='browser'
import kaleido
import os

def makehourindex(intg, delta):
    if intg == 24:
        hr = datetime.time(0)
    else:
        hr = datetime.time(intg)


    if intg +delta == 24:
        hr1 =datetime.time(0)
    else:
        hr1 = datetime.time(intg+delta)

    if delta >= 0:
        return '{}-{}'.format(hr.strftime(format = '%H:%M'),hr1.strftime(format = '%H:%M'))
    else:
        return '{}-{}'.format(hr1.strftime(format = '%H:%M'),hr.strftime(format = '%H:%M'))

def get_prices():
    base_url = 'https://www.epexspot.com/en/market-data?market_area=NL&trading_date={}&delivery_date={}&underlying_year=&modality=Auction&sub_modality=DayAhead&technology=&product=60&data_mode=table&period=&production_period='


    td = datetime.date.today()
    dd = td+datetime.timedelta(days = 1)

    url = base_url.format(str(td),str(dd))

    table = pd.read_html(url)[0]
    prices = table[table.columns[3]]/1000
    prices.name = 'Prijs (€/MWh)'

    lst = []
    for i in range(len(prices)):
        lst.append(makehourindex(prices.index[i],1))

    prices.index = lst
    pricesincl = round((prices+0.03679+0.0305)*1.09,4)

    sort = pricesincl.sort_values(ascending = False)
    duursteuur = "€"+str(round(sort.iloc[0],3))
    time = sort.index[0]
    del sort

    duurste = '{}: {}'.format(time,duursteuur)

    sort = pricesincl.sort_values()
    goedkoopsteuur = "€"+str(round(sort.iloc[0],3))
    time = sort.index[0]

    del sort

    goedkoopste = '{}: {}'.format(time,goedkoopsteuur)

    s = pd.Series(index = pricesincl.index, dtype = float)

    for i in range(1,len(s.index)):
      s.iloc[i] = pricesincl.iloc[i-1:i+1].mean()

    s = s.drop('00:00-01:00')

    lst = []
    for i in range(2,25):
        lst.append(makehourindex(i,-2))

    s.index = lst

    ochtend = s[range(1,8)].sort_values()
    middag = s[range(8,16)].sort_values()
    avond =  s[range(17,23)].sort_values()

    time = ochtend.index[0]
    prijsochtend = round(ochtend[time],3)
    strochtend = '{}: €{}'.format(time,prijsochtend)

    time = middag.index[0]
    prijsmiddag = round(middag[time],3)
    strmiddag = '{}: €{}'.format(time,prijsmiddag)

    time = avond.index[0]
    prijsavond = round(avond[time],3)
    stravond = '{}: €{}'.format(time,prijsavond)


    s = pd.Series(index = pricesincl.index, dtype = float)

    for i in range(2,len(s.index)):
      s.iloc[i] = pricesincl.iloc[i-2:i+1].mean()

    s = s.drop(['00:00-01:00','01:00-02:00'])

    lst = []
    for i in range(3,25):
        lst.append(makehourindex(i,-3))

    s.index = lst

    dag = s.sort_values()

    time = dag.index[0]
    prijsdag = round(dag[time],3)
    strdag = '{}: €{}'.format(time,prijsdag)

    tweet = "Prijscurve voor morgen!\nDuurste uur:\n{}\nGoedkoopste uur:\n{}\nGoedkoopste aaneengesloten uren:\n\
    hele dag:   {}\n\'s Morgens: {}\n\'s Middags: {}\n\'s Avonds:  {}" \
            .format(duurste,goedkoopste,strdag,strochtend,strmiddag,stravond)

    print(tweet)
    prices.index = pd.date_range(start = '2020-01-01', freq = 'H', periods = 24).strftime('%H:%M')
    pricesincl.index = prices.index

    url = 'https://www.overstappen.nl/energie/energietarieven/#Overzicht_energietarieven_2022'
    table = pd.read_html(url)[0]
    table.columns = table.iloc[0]
    table = table.drop(0, axis = 0)
    try:
        mean = pd.Series(table[table.columns[3]]).str.strip('€').str.replace(',','.').astype(float).mean()
    except:
        mean = pd.Series(table[table.columns[1]]).str.strip('€').str.replace(',','.').astype(float).mean()
    mean = prices-prices+mean
    return tweet, mean, prices, pricesincl

def make_figure(mean,prices,pricesincl):
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
        title="Elektriciteitsprijs (€/kWh) "+ dd.strftime("%d-%m-%Y"),
        xaxis_title="Tijd")
    fig.update_xaxes(dtick = 2, tickangle = 45)

    if min(prices)>0:
        fig.update_yaxes(rangemode="tozero")

    filename = 'figs/prijscurve '+dd.strftime('%d%m%Y')+'.jpg'

    return fig, filename

'''
fig.write_image(filename)

auth = tweepy.OAuthHandler(tokens.APIKey, tokens.APISecret)
auth.set_access_token(tokens.AccessToken, tokens.AccessSecret)
api = tweepy.API(auth)

media = api.media_upload(filename)
imgs = [media.media_id_string]
os.remove(filename)


client = tweepy.Client(consumer_key=tokens.APIKey,
                       consumer_secret=tokens.APISecret,
                       access_token=tokens.AccessToken,
                       access_token_secret=tokens.AccessSecret)

client.create_tweet(text = tweet, media_ids = imgs)
'''
