import pandas as pd
import scenario_tools as sw


cpp = pd.read_csv('data/conv_power_plants_DE.edited.csv', index_col='id')
del cpp['Unnamed: 0']

print(cpp.columns)
p = sw.read_parameters('my_scenarios', 'reegis_de_3_short.csv')

cpp['max_in'] = cpp['capacity_net_bnetza'] / cpp['efficiency_estimate']


cpp_by_region_fuel = cpp.groupby(['region', 'fuel'])
print(cpp.groupby('fuel').sum()['capacity_net_bnetza'])
capacity_by_region_fuel = cpp_by_region_fuel[['capacity_net_bnetza',
                                              'capacity_gross_uba',
                                              'max_in']].sum()

capacity_by_region_fuel['eff_new'] = (
    capacity_by_region_fuel.capacity_net_bnetza /
    capacity_by_region_fuel.max_in)
# print(capacity_by_region_fuel.index)
# capacity_by_region_fuel.set_index('region')

for reg in cpp.groupby('region').sum().index:
    print('********{0}*******'.format(reg))
    print(capacity_by_region_fuel.loc[reg, ['capacity_net_bnetza', 'eff_new']])
print(cpp[cpp.region == 'DE19'])
print(cpp[cpp.region == 'DE20'])
print(cpp[cpp.region == 'DE21'])
# print(cpp_by_region_fuel[['efficiency_data', 'efficiency_estimate']].mean())
