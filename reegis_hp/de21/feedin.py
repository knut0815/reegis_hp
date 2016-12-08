import pandas as pd

my = pd.read_hdf('data/renewable_power_plants_DE.edited.hdf', 'data')
p_installed_by_coastdat_id = my.groupby(
    ['coastdat_id', 'energy_source_level_2']).electrical_capacity.sum()

for cd2_id, new_df in p_installed_by_coastdat_id.groupby(level=0):
    a = new_df[cd2_id].get('Solar')

print(a)
