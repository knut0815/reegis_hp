__copyright__ = "Uwe Krien"
__license__ = "GPLv3"

import pandas as pd
import os
import calendar
import logging
import shapely.wkt as wkt
from reegis_hp.de21 import tools
from reegis_hp.de21 import config as cfg
from oemof.tools import logger


try:
    import oemof.db.coastdat as coastdat
    import oemof.db as db
    from sqlalchemy import exc
except ImportError:
    coastdat = None
    db = None
    exc = None


def get_average_wind_speed(weather_path, grid_geometry_file, geometry_path,
                           in_file_pattern, out_file, overwrite=False):
    """
    Get average wind speed over all years for each coastdat region. This can be
    used to select the appropriate wind turbine for each region
    (strong/low wind turbines).
    
    Parameters
    ----------
    overwrite : boolean
        Will overwrite existing files if set to 'True'.
    weather_path : str
        Path to folder that contains all needed files.
    geometry_path : str
        Path to folder that contains geometry files.   
    grid_geometry_file : str
        Name of the geometry file of the weather data grid.
    in_file_pattern : str
        Name of the hdf5 weather files with one wildcard for the year e.g.
        weather_data_{0}.h5
    out_file : str
        Name of the results file (csv)
    """
    if not os.path.isfile(os.path.join(weather_path, out_file)) or overwrite:
        logging.info("Calculating the average wind speed...")

        # Finding existing weather files.
        filelist = (os.listdir(weather_path))
        years = list()
        for y in range(1970, 2020):
                if in_file_pattern.format(year=y) in filelist:
                    years.append(y)

        # Loading coastdat-grid as shapely geometries.
        polygons_wkt = pd.read_csv(os.path.join(geometry_path,
                                                grid_geometry_file))
        polygons = pd.DataFrame(tools.postgis2shapely(polygons_wkt.geom),
                                index=polygons_wkt.gid, columns=['geom'])

        # Opening all weather files
        store = dict()

        # open hdf files
        for year in years:
            store[year] = pd.HDFStore(os.path.join(
                weather_path, in_file_pattern.format(year=year)), mode='r')
        logging.info("Files loaded.")

        keys = store[years[0]].keys()
        logging.info("Keys loaded.")

        n = len(list(keys))
        logging.info("Remaining: {0}".format(n))
        for key in keys:
            wind_speed_avg = pd.Series()
            n -= 1
            if n % 100 == 0:
                logging.info("Remaining: {0}".format(n))
            weather_id = int(key[2:])
            for year in years:
                # Remove entries if year has to many entries.
                if calendar.isleap(year):
                    h_max = 8784
                else:
                    h_max = 8760
                ws = store[year][key]['v_wind']
                surplus = h_max - len(ws)
                if surplus < 0:
                    ws = ws.ix[:surplus]

                # add wind speed time series
                wind_speed_avg = wind_speed_avg.append(
                    ws, verify_integrity=True)

            # calculate the average wind speed for one grid item
            polygons.loc[weather_id, 'v_wind_avg'] = wind_speed_avg.mean()

        # Close hdf files
        for year in years:
            store[year].close()

        # write results to csv file
        polygons.to_csv(os.path.join(weather_path, out_file))
    else:
        logging.info("Skipped: Calculating the average wind speed.")


def calculate_average_temperature_by_region(year):
    """
    Calculate the average temperature for every de21-region.

    Parameters
    ----------
    year : int
        Select the year you want to calculate the average temperature for.

    """
    weatherfile = os.path.join(
        cfg.get('paths', 'weather'),
        cfg.get('weather', 'file_pattern').format(year=year))
    groupingfile = os.path.join(
        cfg.get('paths', 'geometry'),
        cfg.get('geometry', 'intersection_coastdat_de21'))
    outfile = os.path.join(
        cfg.get('paths', 'weather'),
        cfg.get('weather', 'avg_temperature').format(year=year))
    groups = pd.read_csv(groupingfile, index_col=[0, 1, 2])
    groups = groups.swaplevel(0, 2).sort_index()
    weather = pd.HDFStore(weatherfile, mode='r')

    temperature = pd.DataFrame()
    for region in groups.index.get_level_values(0).unique():
        cid_list = groups.loc[region].index.get_level_values(0).unique()
        number_of_sets = len(cid_list)
        tmp = pd.DataFrame(index=weather['A' + str(cid_list[0])].index)
        for cid in groups.loc[region].index.get_level_values(0).unique():
            key = 'A' + str(cid)
            tmp[cid] = weather[key]['temp_air']
        temperature[region] = tmp.sum(1).div(number_of_sets)
    weather.close()
    temperature.to_csv(outfile)
    logging.info("Average temperature saved to {0}".format(outfile))
    return outfile


def fetch_coastdat2_year_from_db(years=None, overwrite=False):
    """Fetch coastDat2 weather data sets from db and store it to hdf5 files.
    this files has to be adapted if the new weather data base is available.

    Parameters
    ----------
    overwrite : boolean
        Skip existing files if set to False.
    years : list of integer
        Years to fetch.
    """
    weather = os.path.join(cfg.get('paths', 'weather'),
                           cfg.get('weather', 'file_pattern'))
    geometry = os.path.join(cfg.get('paths', 'geometry'),
                            cfg.get('geometry', 'germany_polygon'))

    polygon = wkt.loads(
        pd.read_csv(geometry, index_col='gid', squeeze=True)[0])

    if years is None:
        years = range(1980, 2020)

    try:
        conn = db.connection()
    except exc.OperationalError:
        conn = None
    for year in years:
        if not os.path.isfile(weather.format(year=str(year))) or overwrite:
            logging.info("Fetching weather data for {0}.".format(year))

            try:
                weather_sets = coastdat.get_weather(conn, polygon, year)
            except AttributeError:
                logging.warning("No database connection found.")
                weather_sets = list()
            if len(weather_sets) > 0:
                logging.info("Success. Store weather data to {0}.".format(
                    weather.format(year=str(year))))
                store = pd.HDFStore(weather.format(year=str(year)), mode='w')
                for weather_set in weather_sets:
                    logging.debug(weather_set.name)
                    store['A' + str(weather_set.name)] = weather_set.data
                store.close()
            else:
                logging.warning("No weather data found for {0}.".format(year))
        else:
            logging.info("Weather data for {0} exists. Skipping.".format(year))


def coastdat_id2coord():
    """
    Creating a file with the latitude and longitude for all coastdat2 data sets.
    """
    conn = db.connection()
    sql = "select gid, st_x(geom), st_y(geom) from coastdat.spatial;"
    results = (conn.execute(sql))
    columns = results.keys()
    data = pd.DataFrame(results.fetchall(), columns=columns)
    data.set_index('gid', inplace=True)
    data.to_csv(os.path.join('data', 'basic', 'id2latlon.csv'))


if __name__ == "__main__":
    logger.define_logging()
    fetch_coastdat2_year_from_db()
    # calculate_average_temperature_by_region(2013)
