import easygui_qt as easy
import pandas as pd
import numpy as np
import geoplot
from matplotlib import pyplot as plt
import math
from matplotlib.colors import LinearSegmentedColormap

MTH = {'sum': np.sum, 'max': np.max, 'min': np.min, 'mean': np.mean}


class SpatialData:
    def __init__(self, result_file=None):
        if result_file is None:
            result_file = easy.get_file_names(title="Select result file.")[0]
        self.results = pd.read_csv(result_file, index_col=[0, 1, 2])
        self.polygons = None
        self.lines = None
        self.plotter = None

    def add_polygon_column(self, obj=None, direction=None, bus=None,
                           method=None, kws=None, **kwargs):
        if method is None:
            method = easy.get_choice("Chose you method!",
                                     choices=['sum', 'max', 'min', 'mean'])
        if self.polygons is None:
            self.polygons = load_geometry(**kwargs)
        if kws is None:
            kws = ['line', 'GL', 'duals']
        objects = list(set([
            x[5:] for x in
            self.results.index.get_level_values('obj_label').unique()
            if not any(y in x for y in kws)]))
        reg_buses = list(set([
            x[5:] for x in
            self.results.index.get_level_values('bus_label').unique()
            if not any(y in x for y in kws)]))
        global_buses = list(set([
            x for x in
            self.results.index.get_level_values('bus_label').unique()
            if 'GL' in x]))

        buses = reg_buses + global_buses

        if obj is None:
            obj = easy.get_choice("What object do you want to plot?",
                                  choices=objects)

        if direction is None:
            direction = easy.get_choice("From bus or to bus?",
                                        choices=['from_bus', 'to_bus'])

        if bus is None:
            bus = easy.get_choice("Which bus?", choices=buses)

        for r in self.polygons.index:
            try:
                tmp = pd.Series(self.results.loc[
                    '{0}_{1}'.format(r, bus), direction,
                    '{0}_{1}'.format(r, obj)]['val']).groupby(
                        level=0).agg(MTH[method])[0]
            except KeyError:
                tmp = float('nan')
            self.polygons.loc[r, obj] = tmp

        uv = unit_round(self.polygons[obj])
        self.polygons[obj] = uv['series']
        self.polygons[obj].prefix = uv['prefix']
        self.polygons[obj].prefix_long = uv['prefix_long']
        selection = {'obj': obj,
                     'direction': direction,
                     'bus': bus,
                     'method': method}
        return selection
        
    def add_power_lines(self, method=None, **kwargs):
        if self.lines is None:
            self.lines = load_geometry(region_column='name', **kwargs)

        if self.plotter is None:
            self.plotter = geoplot.GeoPlotter(
                geoplot.postgis2shapely(self.lines.geom), (3, 16, 47, 56))
        else:
            self.plotter.geometries = geoplot.postgis2shapely(self.lines.geom)

        if method is None:
            method = easy.get_choice("Chose you method!",
                                     choices=['sum', 'max', 'min', 'mean'])

        for l in self.lines.index:
            try:
                r = l.split('-')
                tmp = pd.Series()
                tmp.set_value(1, self.results.loc[
                    '{0}_bus_el'.format(r[0]), 'from_bus',
                    '{0}_{1}_powerline'.format(*r)]['val'].groupby(
                        level=0).agg(MTH[method])[0])
                tmp.set_value(2, self.results.loc[
                    '{0}_bus_el'.format(r[1]), 'from_bus',
                    '{1}_{0}_powerline'.format(*r)]['val'].groupby(
                        level=0).agg(MTH[method])[0])
                self.lines.loc[l, 'trans'] = tmp.max()
            except KeyError:
                self.lines.loc[l, 'trans'] = 3000000
        uv = unit_round(self.lines['trans'])
        self.lines['trans'] = uv['series']
        self.lines['trans'].prefix = uv['prefix']
        self.lines['trans'].prefix_long = uv['prefix_long']
        return method


def load_geometry(geometry_file=None, region_column='gid'):
    if geometry_file is None:
        geometry_file = easy.get_file_names()[0]
    return pd.read_csv(geometry_file, index_col=region_column)


def show():
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


def unit_round(values, min_value=False):

        longprefix = {0: '', 1: 'kilo', 2: 'Mega', 3: 'Giga', 4: 'Tera',
                      5: 'Exa', 6: 'Peta'}
        shortprefix = {0: '', 1: 'k', 2: 'M', 3: 'G', 4: 'T',
                       5: 'E', 6: 'P'}

        if min_value:
            def_value = min(values)
            a = 1
        else:
            def_value = max(values)
            a = 0
        if def_value > 0:
            factor = int(int(math.log10(def_value)) / 3) + a
        else:
            factor = 0
        values = round(values / 10 ** (factor * 3), 2)

        return {'series': values, 'prefix': shortprefix[factor],
                'prefix_long': longprefix[factor]}


def polygon_plot(l_min=None, l_max=None, setname=None, myset=None, method=None,
                 filename=None):
    geometry = 'geometries/polygons_de21.csv'
    sets = {
        'load': {
            'obj': 'load',
            'direction': 'from_bus',
            'bus': 'bus_el'},
        'pv': {
            'obj': 'solar',
            'direction': 'to_bus',
            'bus': 'bus_el'},
    }
    if setname is None and myset is None:
        setname = easy.get_choice("What object do you want to plot?",
                                  choices=tuple(sets.keys()))
    if setname is not None:
        myset = sets[setname]
    if method is None:
        myset['method'] = easy.get_choice(
            "Chose you method!", choices=['sum', 'max', 'min', 'mean'])
    else:
        myset['method'] = method
    s_data = SpatialData(filename)
    myset = s_data.add_polygon_column(geometry_file=geometry, **myset)

    if myset['method'] == 'sum':
        unit = 'Wh'
    else:
        unit = 'W'
    unit = "[{0}]".format(s_data.polygons[myset['obj']].prefix + unit)

    plotter = geoplot.GeoPlotter(geoplot.postgis2shapely(s_data.polygons.geom),
                                 (3, 16, 47, 56))

    v_min = s_data.polygons[myset['obj']].min()
    v_max = s_data.polygons[myset['obj']].max()
    s_data.polygons['normalised'] = ((s_data.polygons[myset['obj']] - v_min) /
                                     (v_max - v_min))
    plotter.data = s_data.polygons['normalised']
    plotter.plot(facecolor='data', edgecolor='white')
    if l_min is None:
        l_min = v_min
    if l_max is None:
        l_max = v_max

    plotter.draw_legend((l_min, l_max), number_ticks=3, legendlabel=unit,
                        location='bottom')
    show()


def powerline_plot(l_min=None, l_max=None):
    s_data = SpatialData()
    reg = {
        'geometry_file': 'geometries/polygons_de21.csv'}
    poly = geoplot.postgis2shapely(load_geometry(**reg).geom)
    plotter = geoplot.GeoPlotter(poly, (3, 16, 47, 56))
    method = s_data.add_power_lines(
        geometry_file='geometries/lines_de21.csv')
    plotter.plot(facecolor='grey', edgecolor='white')

    if method == 'sum':
        unit = 'Wh'
    else:
        unit = 'W'
    unit = "[{0}]".format(s_data.lines['trans'].prefix + unit)
    v_min = s_data.lines['trans'].min()
    v_max = s_data.lines['trans'].max()
    s_data.lines['normalised'] = ((s_data.lines['trans'] - v_min) /
                                  (v_max - v_min))
    plotter.geometries = geoplot.postgis2shapely(s_data.lines.geom)
    plotter.data = s_data.lines['normalised']
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, 'green'),
                                                           (0.5, 'yellow'),
                                                           (1, 'red')])
    plotter.plot(edgecolor='data', linewidth=2, cmap=my_cmap)

    if l_min is None:
        l_min = v_min
    if l_max is None:
        l_max = v_max

    plotter.draw_legend((l_min, l_max), number_ticks=3, cmap=my_cmap,
                        legendlabel=unit, location='right')
    show()


def combined_plot():
    s_data = SpatialData()
    obj = s_data.add_polygon_column(
        obj='load', direction='from_bus', bus='bus_el', method='sum',
        geometry_file='geometries/polygons_de21.csv')

    s_data.add_power_lines(
        geometry_file='geometries/lines_de21.csv')

    unit = s_data.polygons[obj].prefix_long

    plotter = geoplot.GeoPlotter(geoplot.postgis2shapely(s_data.polygons.geom),
                                 (3, 16, 47, 56))

    v_min = s_data.polygons[obj].min()
    v_max = s_data.polygons[obj].max()
    s_data.polygons['normalised'] = ((s_data.polygons[obj] - v_min) /
                                     (v_max - v_min))
    plotter.data = s_data.polygons['normalised']
    plotter.plot(facecolor='data', edgecolor='white')

    plotter.draw_legend((v_min, v_max), number_ticks=3, legendlabel=unit,
                        location='bottom')

    unit = s_data.lines['trans'].prefix_long
    v_min = s_data.lines['trans'].min()
    v_max = s_data.lines['trans'].max()
    s_data.lines['normalised'] = ((s_data.lines['trans'] - v_min) /
                                  (v_max - v_min))
    plotter.geometries = geoplot.postgis2shapely(s_data.lines.geom)
    plotter.data = s_data.lines['normalised']
    my_cmap = LinearSegmentedColormap.from_list('mycmap', [(0, 'green'),
                                                           (0.5, 'yellow'),
                                                           (1, 'red')])
    plotter.plot(edgecolor='data', linewidth=2, cmap=my_cmap)

    plotter.draw_legend((v_min, v_max), number_ticks=3,
                        legendlabel=unit, location='right')
    show()

if __name__ == "__main__":
    choice = easy.get_choice(
            "What geometry do you want to plot?", choices=['lines', 'polygons'])
    if choice == 'polygons':
        polygon_plot(l_min=0)
    elif choice == 'lines':
        powerline_plot()
    else:
        print("End!")
