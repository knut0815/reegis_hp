
import pandas as pd
import os


kw = pd.read_csv('data/KW_RE_all.csv')
# del cpp['Unnamed: 0']

print(kw.columns)

kw_sort = kw.groupby(['chp','RE','state','city'])
kw_sortiert=kw_sort[['id','capacity_n']].list()
kw_sortiert.to_csv("kw_sortiert.csv")
#print(cpp_by_region_fuel['efficiency_data',  'efficiency_source', 'efficiency_estimate'].mean())

#a=cpp_by_region_fuel[['capacity_net_bnetza',  'capacity_gross_uba']].sum()
#a.to_csv("a.csv")
#results_path="results"
#file_name = ("grupierung_region_fuel")
#cpp_by_region_fuel.to_csv(os.path.join(results_path, file_name))