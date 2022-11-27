from entsoe import EntsoePandasClient
import pandas as pd
import keys
import datetime

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



def prices_api(country = 'NL', delivery_date = datetime.date.today()+datetime.timedelta(days = 1)):
    client = EntsoePandasClient(api_key=keys.entsoe_api_key)
    
    start = pd.Timestamp(delivery_date, tz='Europe/Brussels')
    end = start+datetime.timedelta(hours = 23)

    prices = client.query_day_ahead_prices(country, start = start, end = end)
    prices.name = 'Prijs (€/MWh), {}'.format(delivery_date)
    return prices

def renewable_forecast_api(country = 'NL', delivery_date = datetime.date.today()+datetime.timedelta(days = 1)):
    client = EntsoePandasClient(api_key=keys.entsoe_api_key)
    
    start = pd.Timestamp(delivery_date, tz='Europe/Brussels')
    end = start+datetime.timedelta(hours = 23)
    
    forecast = client.query_wind_and_solar_forecast(country, start = start, end = end)
    forecast.name = 'Generation forecast, {}'.format(delivery_date)
    return forecast #.resample('H').mean()
    

def load_forecast_api(country = 'NL', delivery_date = datetime.date.today()+datetime.timedelta(days = 1)):
    client = EntsoePandasClient(api_key=keys.entsoe_api_key)
    
    start = pd.Timestamp(delivery_date, tz='Europe/Brussels')
    end = start+datetime.timedelta(hours = 23)
    
    forecast = client.query_load_forecast(country, start = start, end = end)
    forecast.name = 'Generation forecast, {}'.format(delivery_date)
    return forecast #.resample('H').mean()

def prices_web(country = 'NL', delivery_date = datetime.date.today()+datetime.timedelta(days = 1)):
    base_url = 'https://www.epexspot.com/en/market-data?market_area={}&trading_date={}&delivery_date={}&underlying_year=&modality=Auction&sub_modality=DayAhead&technology=&product=60&data_mode=table&period=&production_period='

    trading_date = delivery_date - datetime.timedelta(days = 1)

    url = base_url.format(country, str(trading_date),str(delivery_date))

    table = pd.read_html(url)[0]
    prices = table[table.columns[3]]/1000
    prices.name = 'Prijs (€/MWh), {}'.format(delivery_date)
    l = []
    for n in str(delivery_date).split('-'):
        l.append(int(n))
    ind_start = pd.Timestamp(datetime.datetime(l[0],l[1],l[2]),tz = 'Europe/Brussels')
    ind_end = ind_start+datetime.timedelta(hours = 23)
    prices.index = pd.date_range(ind_start,ind_end, freq = 'H')
    return prices