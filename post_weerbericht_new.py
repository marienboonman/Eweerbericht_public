import os
import sys

import datetime
import tweepy
import kaleido
import pandas as pd

import funnew
import keys as tokens

#################
####INVOERWAARDEN
#################  
energiebelasting = 0.12599 #EXCLUSIEF BTW
btw = 1.21
land = 'NL'
landnaam = 'Nederland'
#################
####CHECK OS
#################  

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

#################
####DATUM KIEZEN
#################
delivery_date = datetime.date.today()+datetime.timedelta(days = 1)

if delivery_date.year == 2024:
    energiebelasting = 0.13165/1.21
#################
####GEGEVENS OPHALEN
#################
#Prijzen
prices = funnew.prices_api(delivery_date = delivery_date)/1000
modelcontract = funnew.modelcontract(prices)
forecasts = pd.DataFrame(index = prices.index)
forecasts['Prices'] = prices.resample('15T').ffill()
forecasts['Prices'] = forecasts['Prices'].fillna(method = 'ffill')
forecasts ['Pricesincl'] = round((forecasts['Prices']+energiebelasting+0.025)*1.21,4)
forecasts['Modelcontract'] = modelcontract

try:
    loadforecast = funnew.load_forecast_api(delivery_date = delivery_date)/1000
    forecasts['Load'] = loadforecast
    Load = True
except:
    Load = False


try:
    renewableforecast = funnew.renewable_forecast_api(delivery_date = delivery_date)/1000
    forecasts['Restlast'] = forecasts['Load'] - renewableforecast.sum(axis = 1)
    RES = True
except:
    RES = False    

#################
####GEGEVENS BEWERKEN
#################   
#stringify index
forecasts.index = forecasts.index.strftime('%H:%M')


#################
####API OPSTARTEN
#################  
auth = tweepy.OAuthHandler(tokens.APIKey, tokens.APISecret)
auth.set_access_token(tokens.AccessToken, tokens.AccessSecret)
api = tweepy.API(auth)

#################
####PLOTS MAKEN
#################  
imgs = []

###PLOT PRIJZEN
fig = funnew.plot_prices(forecasts, landnaam, delivery_date)
filename = 'prijscurve_'+delivery_date.strftime('%d%m%Y')+'.png'

fig.write_image(filename, scale = 2)

media = api.media_upload(filename)
imgs.append(media.media_id_string)
os.remove(filename)
del fig 

if (Load and RES):
    ### PLOT FORECASTS
    fig = funnew.plot_forecasts(forecasts, landnaam, delivery_date)
    filename = 'forecasts_'+delivery_date.strftime('%d%m%Y')+'.png'
    
    fig.write_image(filename, scale = 2)
    
    media = api.media_upload(filename)
    imgs.append(media.media_id_string)
    os.remove(filename)
    del fig 
    
    ###PLOT LASTEN
    fig = funnew.plot_loads(forecasts, 'NL', delivery_date)
    filename = 'loads_'+delivery_date.strftime('%d%m%Y')+'.png'
    
    fig.write_image(filename, scale = 2)
    
    media = api.media_upload(filename)
    imgs.append(media.media_id_string)
    os.remove(filename)
    del fig 

    
#################
####TWEET SCHRIJVEN
#################  
tweet = funnew.write_tweet(forecasts, land)    


#################
####TWEET POSTEN
#################  
client = tweepy.Client(consumer_key=tokens.APIKey,
                       consumer_secret=tokens.APISecret,
                       access_token=tokens.AccessToken,
                       access_token_secret=tokens.AccessSecret)

client.create_tweet(text = tweet, media_ids = imgs)
