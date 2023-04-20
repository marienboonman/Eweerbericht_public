from entsoe import EntsoePandasClient
import pandas as pd
import datetime
import keys

client = EntsoePandasClient(api_key=keys.entsoe_api_key)
#  4a2ed80d-d974-47ef-8d11-778e05f67850
# (api_key=keys.entsoe_api_key)


start = pd.Timestamp(datetime.date.today()+datetime.timedelta(days = 1), tz='Europe/Brussels')
end = start+datetime.timedelta(hours = 23)
country_code = 'NL'  # Nederland

# methods that return XML
prices = client.query_day_ahead_prices(country_code, start = start, end = end)


