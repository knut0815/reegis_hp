
import pandas as pd
import os


ewz = pd.read_csv('data/KR_WR_BL_RE.csv')
# del cpp['Unnamed: 0']

print(ewz.columns)

ewz_RE = ewz.groupby(['REG,N,10,0', 'GEN_2,C,50'])
print(ewz_RE[['EWZ_2,N,11,0']].sum())
#print(cpp_by_region_fuel['efficiency_data',  'efficiency_source', 'efficiency_estimate'].mean())

#a=cpp_by_region_fuel[['capacity_net_bnetza',  'capacity_gross_uba']].sum()
#a.to_csv("a.csv")
#results_path="results"
#file_name = ("grupierung_region_fuel")
#cpp_by_region_fuel.to_csv(os.path.join(results_path, file_name))