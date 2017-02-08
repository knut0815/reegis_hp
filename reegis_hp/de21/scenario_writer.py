"""
The scenario files should end with '.csv'.
The sequence file should have the same name with an addtional '_seq'.
For example: my_example.csv, my_example_seq.csv
"""
import os
import pandas as pd


def update_parameter(name, pattern, query_col, target_col, data, ptype='region',
                     path='scenarios'):
    objects = pd.Series()
    if ptype == 'region':
        objects = pd.read_csv(os.path.join('data_basic', 'region_id.csv'),
                              index_col='region_id')
    elif ptype == 'grid':
        objects = pd.read_csv(os.path.join('data_basic', 'grid_id.csv'),
                              index_col='grid_id')
        objects.index = (objects.index.str.replace('-', '_'))

    scenario = pd.read_csv(os.path.join(path, name + '.csv'), index_col='class')

    for object_id in objects.index:
        label = pattern.format(object_id)
        scenario.loc[scenario[query_col] == label, target_col] = (
            data.loc[object_id])
    scenario.to_csv(os.path.join(path, name + '.csv'))


def update_sequence(name, path):
    full_path_seq = os.path.join(path, name + '_seq')
    columns = pd.read_csv(full_path_seq + '.csv', header=1, nrows=1).columns
    tmp_csv = pd.read_csv(full_path_seq + '.csv', skiprows=5, names=columns,
                          index_col='label', parse_dates=True)
    print(tmp_csv)


if __name__ == '__main__':
    values = pd.read_csv(os.path.join('data', 'de_grid.csv'),
                         index_col='name').capacity
    values.index = (values.index.str.replace('-', '_'))
    update_parameter('reegis_de_21_writer', '{0}_powerline', 'source',
                     'nominal_value', values, 'grid')
    # update_sequence('reegis_de_21_writer', 'scenarios')
