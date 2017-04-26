import pandas as pd
import os
from matplotlib import pyplot as plt
import geoplot
try:
    import oemof.db.coastdat as coastdat
    import oemof.db as db
except ImportError:
    coastdat = None
    db = None
from shapely.wkt import loads
import logging
from oemof.tools import logger


def add_labels(data, plot_obj, column=None, coord_file=None, textcolour='blue'):
    """
    Add labels to a geoplot.

    Parameters
    ----------
    data : pandas.DataFrame
    plot_obj : geoplot.plotter
    column : str
    coord_file : str
    textcolour : str

    Returns
    -------

    """

    if coord_file is not None:
        p = pd.read_csv(coord_file, index_col='name')
        data = pd.concat([data, p], axis=1)

    for row in data.iterrows():
        if 'point' not in row[1]:
            point = geoplot.postgis2shapely([row[1].geom, ])[0].centroid
        else:
            print(row[1].point)
            point = geoplot.postgis2shapely([row[1].point, ])[0]
        (x, y) = plot_obj.basemap(point.x, point.y)
        if column is None:
            text = str(row[0])
        else:
            text = str(row[1][column])

        plot_obj.ax.text(x, y, text, color=textcolour, fontsize=12)


def draw_line(plot_obj, start, end, color='black'):
    start_line = plot_obj.basemap(start[0], start[1])
    end_line = plot_obj.basemap(end[0], end[1])
    plt.plot([start_line[0], end_line[0]], [start_line[1], end_line[1]], '-',
             color=color)


def plot_geocsv(filepath, idx_col, facecolor=None, edgecolor='#aaaaaa',
                bbox=(3, 16, 47, 56), labels=True, **kwargs):
    df = pd.read_csv(filepath, index_col=idx_col)

    plotter = geoplot.GeoPlotter(geoplot.postgis2shapely(df.geom), bbox)
    plotter.plot(facecolor=facecolor, edgecolor=edgecolor)

    if labels:
        add_labels(df, plotter, **kwargs)

    plt.tight_layout()
    plt.box(on=None)
    plt.show()


def read_seq_file():
    seq_file = 'scenarios/reegis_de_21_test_neu_seq.csv'
    seq_neu = 'scenarios/reegis_de_21_test_neu_neu_seq.csv'

    tmp_csv = pd.read_csv(seq_file, header=[0, 1, 2, 3, 4],
                          parse_dates=True, index_col=0)

    tmp_csv.to_csv(seq_neu)
    print(tmp_csv.index)


def fetch_coastdat2_year_from_db(years=range(1980, 2020), overwrite=False):
    """Fetch coastDat2 weather data sets from db and store it to hdf5 files.

    Parameters
    ----------
    overwrite : boolean
        Skip existing files if set to False.
    years : list of integer
        Years to fetch.

    """
    weather_path = os.path.join('data', 'weather', 'coastDat2_de_{0}.h5')
    geometry_path = os.path.join('data', 'geometries', 'germany.csv')

    if not os.path.isdir('data'):
        os.makedirs('data')
    if not os.path.isdir(os.path.join('data', 'weather')):
        os.makedirs(os.path.join('data', 'weather'))

    polygon = loads(
        pd.read_csv(geometry_path, index_col='gid', squeeze=True)[0])

    conn = db.connection()
    for year in years:
        if not os.path.isfile(weather_path.format(str(year))) or overwrite:
            weather_sets = coastdat.get_weather(conn, polygon, year)
            if len(weather_sets) > 0:
                logging.info("Fetching weather data for {0}.".format(year))
                store = pd.HDFStore(weather_path.format(str(year)), mode='w')
                for weather_set in weather_sets:
                    logging.debug(weather_set.name)
                    store['A' + str(weather_set.name)] = weather_set.data
                store.close()
            else:
                logging.warning("No weather data found for {0}.".format(year))
        else:
            logging.info("Weather data for {0} exists. Skipping.".format(year))
    

if __name__ == "__main__":
    # plot_geocsv(os.path.join('geometries', 'federal_states.csv'),
    #             idx_col='iso',
    #             coord_file='data_basic/label_federal_state.csv')
    plot_geocsv(os.path.join('data', 'geometries', 'polygons_de21_simple.csv'),
                idx_col='gid',
                # coord_file=os.path.join('data_basic', 'centroid_region.csv')
                )
    # plot_geocsv('/home/uwe/geo.csv', idx_col='gid')
    logger.define_logging()
    # fetch_coastdat2_year_from_db()
