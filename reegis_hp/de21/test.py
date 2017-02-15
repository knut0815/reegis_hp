import pandas as pd

seq_file = 'scenarios/reegis_de_21_test_neu_seq.csv'
seq_neu = 'scenarios/reegis_de_21_test_neu_neu_seq.csv'

tmp_csv = pd.read_csv(seq_file, header=[0, 1, 2, 3, 4],
                      parse_dates=True, index_col=0)

tmp_csv.to_csv(seq_neu)
print(tmp_csv.index)
