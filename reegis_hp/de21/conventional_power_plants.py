import pandas as pd

cpp = pd.read_csv('data/conv_power_plants_DE.edited.csv', index_col='id')
del cpp['Unnamed: 0']

print(cpp.columns)

cpp_by_region_fuel = cpp.groupby(['region', 'fuel'])

capacity_by_region_fuel = cpp_by_region_fuel[['capacity_net_bnetza',
                                              'capacity_gross_uba']].sum()

print(capacity_by_region_fuel)
print(cpp_by_region_fuel[['efficiency_data', 'efficiency_estimate']].mean())
