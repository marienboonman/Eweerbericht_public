from entsoe import EntsoePandasClient
import pandas as pd
import keys
import datetime

client = EntsoePandasClient(api_key=keys.entsoe_api_key)

start = pd.Timestamp(datetime.date.today()+datetime.timedelta(days = 1), tz='Europe/Brussels')
end = start+datetime.timedelta(hours = 23)
country_code = 'NL'  # Nederland

# methods that return XML
prices = client.query_day_ahead_prices(country_code, start = start, end = end)
