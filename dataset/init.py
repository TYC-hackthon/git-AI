# %%
import pandas as pd
import requests

import re, json

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

ans = ans.reset_index()
# %%
ans.to_csv('ds.csv', index = False)

# %%
filter = re.compile(r'^SAT READING COMPREHENSION TEST\n*(.+)\n*Question (\d+):\n*(.+)\n*Answer:$', flags = re.MULTILINE | re.DOTALL)

# %%
filter.findall(ans.iloc[29].text)

# %%
ans['re'] = ans.text.map(lambda x: filter.findall(x))

# %%
ans['paragraph'] = ans.re.map(lambda x: x[0][0])
ans['qid'] = ans.re.map(lambda x: x[0][1])
ans['question'] = ans.re.map(lambda x: x[0][2])

# %%
id_filter = re.compile(r'^sat-practice_(\d+)-question_(\d+)$')

# %%
ans['re'] = ans.id.map(lambda x: id_filter.findall(x))

ans['pid'] = ans.re.map(lambda x: x[0][0])
ans['tqid'] = ans.re.map(lambda x: x[0][1])

assert(all(ans.qid == ans.tqid))

# %%
ans['gid'] = pd.to_numeric(ans.pid)
ans['qid'] = pd.to_numeric(ans.qid)

# %%
ans = ans.sort_values(['gid', 'qid'])
ans = ans.drop(['re', 'tqid', 'index'], axis = 1)

# %%
ans = ans.reset_index(drop = True)

# %%
mapper = {i: j + 1 for j, i in enumerate(ans.paragraph.unique())}

# %%
ans['pid'] = ans.paragraph.map(lambda x: mapper[x])

# %%
assert len(ans.groupby('pid').paragraph.unique().map(lambda x: len(x)).unique()) == 1

# %%

# %%
ans.to_csv('ds.csv', index = False)


