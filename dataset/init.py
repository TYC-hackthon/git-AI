# %%
import pandas as pd
import requests

import json

rq = requests.Session()

# %%
url = lambda x: f'https://datasets-server.huggingface.co/rows?dataset=emozilla%2Fsat-reading&config=default&split=train&offset={100 * x}&length=100'

# %%
def get(url: str):
    pre = rq.get(url).text
    f = json.loads(pre)
    v = [f['rows'][i]['row'] for i in range(len(f['rows']))]
    return pd.DataFrame(v)

# %%
ans = pd.DataFrame()
now = 0

while True:
    tmp = get(url(now))
    now += 1
    if tmp.empty:
        break
    ans = pd.concat([ans, tmp])

# %%
ans.to_csv('ds.csv', index = False)

# %%



