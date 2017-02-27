import pandas as pd

seq_file = 'scenarios/reegis_de_21_test_neu_seq.csv'
# seq_neu = 'scenarios/reegis_de_21_test_neu_neu_seq.csv'
# para_file = 'scenarios/reegis_de_3_test.csv'
para_file = 'scenarios/EK_test3_neu2.csv'
seq_neu = 'scenarios/EK_test3_neu2_seq.csv'

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

