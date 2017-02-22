import pandas as pd

cpp = pd.read_csv('data/conv_power_plants_DE.edited.csv', index_col='id')
del cpp['Unnamed: 0']

cpp['max_in'] = cpp['capacity_net_bnetza'] / cpp['efficiency_estimate']

cpp_by_region_fuel = cpp.groupby(['region', 'state', 'fuel'])

capacity_by_region_fuel = cpp_by_region_fuel[['capacity_net_bnetza',
                                              'capacity_gross_uba',
                                              'max_in']].sum()

capacity_by_region_fuel['eff_new'] = (
    capacity_by_region_fuel.capacity_net_bnetza /
    capacity_by_region_fuel.max_in)
# print(capacity_by_region_fuel.index)
# capacity_by_region_fuel.set_index('region')


print(capacity_by_region_fuel.loc['DE15', ['capacity_net_bnetza', 'eff_new']])
# print(cpp_by_region_fuel[['efficiency_data', 'efficiency_estimate']].mean())
