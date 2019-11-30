
# Use seaborn for viz https://seaborn.pydata.org/introduction.html#introduction
import gdelt
import numpy as np
import pandas as pd

gd2 = gdelt.gdelt(version=2)
results = gd2.Search('2019 08 28', table='events', coverage=True)
bio_results = results[results.apply(
    lambda row: row.astype(str).str.contains('biol').any(), axis=1)]
bio_results.to_excel('biores.xls')

for i in bio_results.columns:
    newDf = bio_results.loc[lambda df: hasattr(
        df[i], 'str') and df[i].str.contains('biol')].any()
    if(not newDf.empty):
        print(i)


from datetime import date, timedelta

import gdelt
import numpy as np
import pandas as pd


# Extract themes from the last month
gd2 = gdelt.gdelt(version=2)
themes = set()
today = date.today()
for i in range(1, 31):
    d = today - timedelta(days=i)
    datestring = d.strftime('%Y %m %d')
    past_res_df = gd2.Search(datestring, table='gkg', coverage=True)
    for cell in past_res_df['Themes']:
        for val in cell.values:
            themes.update([v for v in val.split(';') if v])
