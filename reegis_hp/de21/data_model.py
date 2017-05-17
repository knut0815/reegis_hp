import os
import weather


def check_path(pathname):
    if not os.path.isdir(pathname):
        os.makedirs(pathname)
    return pathname


def extend_base_path(name):
    return check_path(os.path.join(base_path, name))


def weather_data(weather_pth, geometry_pth, grid_geometry,
                 weather_file, region_geometry, avg_wind_file, ovw):

    if not os.path.isdir('data'):
        os.makedirs('data')

    # Fetch non-existing weather data from a file. Use overwrite or a new
    # pattern if the region geometry changed.
    weather.fetch_coastdat2_year_from_db(weather_pth, geometry_pth, weather_file,
                                         region_geometry, overwrite=ovw)

    # Calculate the average wind speed for all available weather data sets.
    weather.get_average_wind_speed(weather_pth, grid_geometry, geometry_pth,
                                   weather_file, avg_wind_file)


if __name__ == "__main__":
    overwrite = False
    skip_weather = False
    base_path = check_path(os.path.join(os.path.dirname(__file__), 'data'))
    weather_path = extend_base_path('weather')
    geometry_path = extend_base_path('geometries')
    grid_geometry_file = 'coastdat_grid.csv'
    weather_file_pattern = 'coastDat2_de_{0}.h5'
    region_geometry_file = 'germany.csv'
    average_wind_speed_file_pattern = 'average_wind_speed_{0}_to_{1}.csv'

    # Get weather data
    if not skip_weather:
        weather_data(weather_path, geometry_path, grid_geometry_file,
                     weather_file_pattern, region_geometry_file,
                     average_wind_speed_file_pattern, overwrite)
