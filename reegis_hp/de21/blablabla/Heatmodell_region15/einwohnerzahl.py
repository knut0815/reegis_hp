
import pandas as pd
import os


ew_land = pd.read_csv('data/VG250_LAN.csv', index_col='id')
del ew_land ['GF,N,11,0: 1']
del ew_land ['GF,N,11,0: 2']
del ew_land ['GF,N,11,0: 3']
print(ew_land.columns)

# cpp_by_region_fuel = cpp.groupby(['region', 'fuel'])
# print(cpp_by_region_fuel[['capacity_net_bnetza',  'capacity_gross_uba']].sum())
# print(cpp_by_region_fuel['efficiency_data',  'efficiency_source', 'efficiency_estimate'].mean())

# a=cpp_by_region_fuel[['capacity_net_bnetza',  'capacity_gross_uba']].sum()
print(ew_land)
# a.to_csv("a.csv")
#results_path="results"
#file_name = ("grupierung_region_fuel")
#cpp_by_region_fuel.to_csv(os.path.join(results_path, file_name))