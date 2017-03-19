"""
The scenario files should end with '.csv'.
The sequence file should have the same name with an addtional '_seq'.
For example: my_example.csv, my_example_seq.csv
"""
import os.path as path
import pandas as pd


PARAMETER = (
    'conversion_factors', 'nominal_value',
    'min', 'max', 'summed_max', 'actual_value', 'fixed_costs', 'variable_costs',
    'fixed', 'nominal_capacity', 'capacity_loss', 'inflow_conversion_factor',
    'outflow_conversion_factor', 'initial_capacity', 'capacity_min',
    'capacity_max', 'balanced', 'sort_index')
INDEX = ('class', 'label', 'source', 'target')


class SolphScenario:

    def __init__(self, **kwargs):
        self.p = kwargs.get('parameters')
        self.s = kwargs.get('sequences')
        self.path = kwargs.get('path', path.dirname(path.realpath(__file__)))
        self.name = kwargs.get('name')

    def create_parameter_table(self, additional_parameter=None):
        """Create an empty parameter table."""
        if additional_parameter is None:
            additional_parameter = tuple()

        my_index = pd.MultiIndex(levels=[[], [], [], []],
                                 labels=[[], [], [], []],
                                 names=INDEX)
        self.p = pd.DataFrame(columns=PARAMETER + tuple(additional_parameter),
                              index=my_index)

    def create_sequence_table(self, datetime_index=None, year=None,
                              interval=None):
        """Create an empty sequence table."""
        if interval is None:
            interval = '60min'
        if datetime_index is None:
            date_from = '{0}-01-01 00:00:00'.format(year)
            date_to = '{0}-12-31 23:00:00'.format(year)
            datetime_index = pd.date_range(date_from, date_to, freq=interval)

        my_index = pd.MultiIndex(
            levels=[[1], [2], [3], [4], [5]], labels=[[0], [0], [0], [0], [0]],
            names=INDEX + ('attributes',))

        df = pd.DataFrame(index=datetime_index, columns=my_index)
        del df[1, 2, 3, 4, 5]
        self.s = df

    def create_tables(self, **kwargs):
        self.create_parameter_table(
            additional_parameter=kwargs.get('additional_parameter'))
        self.create_sequence_table(datetime_index=kwargs.get('datetime_index'),
                                   year=kwargs.get('year'),
                                   interval=kwargs.get('interval'))

    def read_parameter_table(self, filename=None):
        """Read parameter table from file."""
        if filename is None:
            filename = path.join(self.path, self.name + '.csv')
        self.p = pd.read_csv(filename, index_col=[0, 1, 2, 3])

    def read_sequence_table(self, filename=None):
        """Read parameter table from file."""
        if filename is None:
            filename = path.join(self.path, self.name + '_seq_.csv')
        self.s = pd.read_csv(filename, header=[0, 1, 2, 3, 4], parse_dates=True,
                             index_col=0)

    def read_tables(self, name=None, scenario_path=None):
        """Read scenario table"""
        if name is not None:
            self.name = name
        if scenario_path is not None:
            self.path = scenario_path
        self.read_parameter_table()
        self.read_sequence_table()

    def write_parameter_table(self, filename=None):
        """Write parameter table to file."""
        if filename is None:
            filename = path.join(self.path, self.name + '.csv')
        self.p = self.p.fillna('')
        self.p.sort_values('sort_index', inplace=True)
        self.p.to_csv(filename)

    def write_sequence_table(self, filename=None):
        """Write sequence table to file."""
        if filename is None:
            filename = path.join(self.path, self.name + '_seq.csv')
        self.s.to_csv(filename)

    def write_tables(self, name=None, scenario_path=None):
        """Read scenario table"""
        if name is not None:
            self.name = name
        if scenario_path is not None:
            self.path = scenario_path
        self.write_parameter_table()
        self.write_sequence_table()

    def create_nodes(self):
        """Create nodes for a solph.energysystem."""
        pass

    def add_parameters(self, idx, columns, values):
        self.p.loc[idx, columns] = values
        self.p = self.p.sortlevel()

    def add_sequences(self, idx, sequence):
        self.s[idx[0], idx[1], idx[2], idx[3], idx[4]] = sequence

    def add_comment_line(self, comment, sort_entry):
        self.p.loc[('### {0}'.format(comment), '', '', ''),
                   'sort_index'] = sort_entry
        self.p = self.p.sortlevel()
