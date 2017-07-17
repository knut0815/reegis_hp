import pandas as pd
import oemof.db as db
import oemof.db.coastdat as coastdat
from shapely.wkt import loads


def fetch_geometries(**kwargs):
    """Reads the geometry and the id of all given tables and writes it to
     the 'geom'-key of each branch of the data tree.
    """
    sql_str = '''
        SELECT {id_col}, ST_AsText(
            ST_SIMPLIFY({geo_col},{simp_tolerance}))
        FROM {schema}.{table}
        WHERE "{where_col}" {where_cond}
        ORDER BY {id_col} DESC;'''

    db_string = sql_str.format(**kwargs)
    return db.connection().execute(db_string).fetchall()


def fetch_coastdat2_year_from_db(years):
    """Fetch coastDat2 weather data sets from db and store it to hdf5 files.

    Parameters
    ----------
    years : list of integer
        Years to fetch.

    """
    conn = db.connection()
    polygon = loads(pd.read_csv('geometries/germany.csv', index_col='gid',
                                squeeze=True)[0])

    for year in years:
        weather_sets = coastdat.get_weather(conn, polygon, year)
        store = pd.HDFStore('coastDat2_de_{0}.h5'.format(str(year)))
        for weather_set in weather_sets:
            print(weather_set.name)
            store['A' + str(weather_set.name)] = weather_set.data
        store.close()
