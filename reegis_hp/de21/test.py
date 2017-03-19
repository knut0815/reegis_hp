import pandas as pd
from matplotlib import pyplot as plt
import logging

from oemof.tools import logger

logger.define_logging()
exit(0)
df = pd.read_csv('/home/uwe/geo.csv', index_col='zip_code')
del df['Unnamed: 0']
del df['gid']
df.to_csv('/home/uwe/git_local/reegis-hp/reegis_hp/de21/geometries/postcode.csv')
exit(0)

df = pd.read_csv('solar_cap.csv', index_col=[0, 1, 2, 3])
# df = df.sortlevel()
# df = df.reindex_axis(sorted(df.columns), axis=1)
df.index = df.index.droplevel(0)
my = df.groupby(level=[0]).sum()

# df_all = pd.Series(df.sum(axis=1), index=df.index)
# my = df_all.unstack(level=0)
# my = my.sortlevel()
my.plot(stacked=True, kind='area')
# plt.show()
# df.loc['Solar'].plot(stacked=True, kind='area')
# df.loc['Solar'].plot()
# plt.show()
df = pd.read_csv('test_cap.csv', index_col=[0, 1]).fillna(0)
df = df.sortlevel()
df = df.reindex_axis(sorted(df.columns), axis=1)

print(df)
df_all = pd.Series(df.sum(axis=1), index=df.index)
my = df_all.unstack(level=0)
my = my.sortlevel()
my.plot(stacked=True, kind='area')
# plt.show()
df.loc['Solar'].plot(stacked=True, kind='area')
df.loc['Solar'].plot()
plt.show()

exit(0)
seq_file = 'my_scenarios/reegis_de_21_test_neu_seq.csv'
# seq_neu = 'scenarios/reegis_de_21_test_neu_neu_seq.csv'
# para_file = 'scenarios/reegis_de_3_test.csv'
para_file = 'my_scenarios/EK_test3_neu2.csv'
seq_neu = 'my_scenarios/EK_test3_neu2_seq.csv'

df_seq = pd.read_csv(seq_neu, header=[0, 1, 2, 3, 4],
                     parse_dates=True, index_col=0)

# tmp_csv.to_csv(seq_neu)
# print(tmp_csv.index)

df = pd.read_csv(para_file, index_col=[0, 1, 2])

mask = df['actual_value'].str.contains('seq').fillna(False)
a = df[mask].index.tolist()
print(a[0])
# print(pd.Series([1, 2, 4]))
# # df.loc[[a[0]], 'actual_value'] = pd.Series([1, 2, 4])
# print(df['actual_value'].loc[[a[0]]])
# s = df.to_dict()
# print(s['actual_value'][a[0]])

print(df_seq[a[0]])

