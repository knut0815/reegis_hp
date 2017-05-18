import pandas as pd
import numpy as np
import os
import calendar
import logging
import shapely.wkt as wkt
import tools
from datetime import datetime as time

try:
    import oemof.db.coastdat as coastdat
    import oemof.db as db
except ImportError:
    coastdat = None
    db = None


def get_average_wind_speed(weather_path, grid_geometry_file, geometry_path,
                           in_file_pattern, out_file_pattern):
    """
    Get average wind speed over all years for each coastdat region. This can be
    used to select the appropriate wind turbine for each region
    (strong/low wind turbines).
    
    Parameters
    ----------
    weather_path : str
        Path to folder that contains all needed files.
    geometry_path : str
        Path to folder that contains geometry files.   
    grid_geometry_file : str
        Name of the geometry file of the weather data grid.
    in_file_pattern : str
        Name of the hdf5 weather files with one wildcard for the year e.g.
        weather_data_{0}.h5
    out_file_pattern : str
        Name of the results file (csv) with two wildcards for first year and
        last year e.g. average_wind_speed_from_{0}_to_{1}.csv
    """
    start = time.now()

    # Finding existing weather files.
    filelist = (os.listdir(weather_path))
    years = list()
    for y in range(1970, 2020):
        if in_file_pattern.format(y) in filelist:
            years.append(y)
    from_year = np.array(years).min()
    to_year = np.array(years).max()

    # Loading coastdat-grid as shapely geometries.
    polygons_wkt = pd.read_csv(os.path.join(geometry_path, grid_geometry_file))
    polygons = pd.DataFrame(tools.postgis2shapely(polygons_wkt.geom),
                            index=polygons_wkt.gid, columns=['geom'])

    # Opening all weather files
    store = dict()

    # open hdf files
    for year in years:
        store[year] = pd.HDFStore(os.path.join(
            weather_path, in_file_pattern.format(year)), mode='r')
    logging.info("Files loaded", time.now() - start)
    keys = store[years[0]].keys()
    logging.info("Keys loaded", time.now() - start)
    firstyear = years[0]
    years.remove(firstyear)
    n = len(list(keys))
    for key in keys:
        n -= 1
        if n % 100 == 0:
            logging.info(n)
        weather_id = int(key[2:])
        wind_speed_avg = store[firstyear][key]['v_wind']
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
            wind_speed_avg = wind_speed_avg.append(ws, verify_integrity=True)

        # calculate the average wind speed for one grid item
        polygons.loc[weather_id, 'v_wind_avg'] = wind_speed_avg.mean()
    years.append(firstyear)

    # Close hdf files
    for year in years:
        store[year].close()

    # write results to csv file
    polygons.to_csv(os.path.join(weather_path, out_file_pattern.format(
        from_year, to_year)))


def fetch_coastdat2_year_from_db(weather_path, geometry_path, out_file_pattern,
                                 geometry_file, years=range(1980, 2020),
                                 overwrite=False):
    """Fetch coastDat2 weather data sets from db and store it to hdf5 files.
    this files has to be adapted if the new weather data base is available.

    Parameters
    ----------
    overwrite : boolean
        Skip existing files if set to False.
    years : list of integer
        Years to fetch.
    weather_path : str
        Path to folder that contains all needed files.
    geometry_path : str
        Path to folder that contains geometry files.
    geometry_file : str
        Name of the geometry file to clip the weather data set.
    out_file_pattern : str
        Name of the hdf5 weather files with one wildcard for the year e.g.
        weather_data_{0}.h5

    """
    weather = os.path.join(weather_path, out_file_pattern)
    geometry = os.path.join(geometry_path, geometry_file)

    polygon = wkt.loads(
        pd.read_csv(geometry, index_col='gid', squeeze=True)[0])

    conn = db.connection()
    for year in years:
        if not os.path.isfile(weather.format(str(year))) or overwrite:
            weather_sets = coastdat.get_weather(conn, polygon, year)
            if len(weather_sets) > 0:
                logging.info("Fetching weather data for {0}.".format(year))
                store = pd.HDFStore(weather.format(str(year)), mode='w')
                for weather_set in weather_sets:
                    logging.debug(weather_set.name)
                    store['A' + str(weather_set.name)] = weather_set.data
                store.close()
            else:
                logging.warning("No weather data found for {0}.".format(year))
        else:
            logging.info("Weather data for {0} exists. Skipping.".format(year))
