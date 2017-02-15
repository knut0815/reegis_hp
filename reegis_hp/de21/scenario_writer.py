"""
The scenario files should end with '.csv'.
The sequence file should have the same name with an addtional '_seq'.
For example: my_example.csv, my_example_seq.csv
"""
import os
import pandas as pd
from shutil import copyfile


def update_parameter(name, pattern, query_col, target_col, data, object_path,
                     scenario_path='scenarios'):
    """
    Updating parameters in a csv file (oemof csv format).

    Parameters
    ----------
    name : str
        basic name of the csv file
    pattern : str
        Basic string containing a format placeholder
    query_col : str
        column name in which the the search string (pattern + object name) can
        be found.
    target_col : str
        column name in which the parameter should be changed
    data : pandas.Series
        Series containing the data to update the parameters. Index values must
        be equal to the object names.
    object_path : str
        Path to a csv file containing a list of object names separated by a
        line break.
    scenario_path
        Path where the scenario files can be found (default: 'scenarios')

    """
    objects = pd.read_csv(object_path, index_col=0)
    scenario = pd.read_csv(os.path.join(scenario_path, name + '.csv'),
                           index_col='class')

    for object_id in objects.index:
        label = pattern.format(object_id)
        scenario.loc[scenario[query_col] == label, target_col] = (
            data.loc[object_id])
    scenario.to_csv(os.path.join(scenario_path, name + '.csv'))


def update_sequence(name, pattern, data, object_path, scenario_path='scenarios',
                    backup=True):
    """
    Updating sequences in a csv file (oemof csv format).

    Parameters
    ----------
    name : str
        basic name of the csv file
    pattern : str
        Basic string containing a format placeholder
    data : pandas.Series
        Series containing the data to update the parameters. Column names must
        equal to object names.
    object_path : str
        Path to a csv file containing a list of object names separated by a
        line break.
    scenario_path
        Path where the scenario files can be found (default: 'scenarios')
    backup : boolean
        Will create an back of the unchanged file if set to True.

    """
    full_path_seq = os.path.join(scenario_path, name + '_seq')
    objects = pd.read_csv(object_path, index_col=0)

    # Create backup file if backup is True
    if backup:
        copyfile(full_path_seq + '.csv', full_path_seq + '.csv.backup')

    # Load table with 'label' as column name
    columns = pd.read_csv(full_path_seq + '.csv', header=1, nrows=1).columns
    tmp_csv = pd.read_csv(full_path_seq + '.csv', skiprows=5, names=columns,
                          parse_dates=True, index_col=0)

    # tmp_csv.drop(0, axis=0, inplace=True)  # remove first line
    # Convert datetime to datetime object and set as index
    # tmp_csv.label = pd.to_datetime(tmp_csv.label)
    # tmp_csv.set_index('label', inplace=True, drop=True)

    # Write data into pandas table
    for object_id in objects.index:
        tmp_csv[pattern.format(object_id)] = list(data[object_id])

    # Extract the header
    with open(full_path_seq + '.csv') as csv_file:
        head = [next(csv_file, x) for x in range(5)]

    # Write data to file using pandas and read it again to get a text block.
    tmp_csv.to_csv(full_path_seq + '~.csv', header=False)
    with open(full_path_seq + '~.csv') as tmp_file:
        body = tmp_file.read()

    # Write data to temporary file for not overwriting existing data
    with open(full_path_seq + '~.csv', 'w') as csv_file:
        for line in head:
            csv_file.write(line)
        csv_file.write(body)

    # Overwrite input file with result file if no error occurred
    os.rename(full_path_seq + '~.csv', full_path_seq + '.csv')

if __name__ == '__main__':
    # values = pd.read_csv(os.path.join('data', 'de_grid.csv'),
    #                      index_col='name').capacity
    #
    # obj_path = os.path.join('data_basic', 'grid_id.csv')
    # update_parameter('reegis_de_21_writer', '{0}_powerline', 'source',
    #                  'nominal_value', values, obj_path)
    obj_path = os.path.join('data_basic', 'region_id.csv')
    data = pd.read_csv(
        os.path.join('weather', 'feedin_pv_de_{0}.csv'.format(2014)))
    update_sequence('reegis_de_21_writer', '{0}_solar', data, obj_path)
