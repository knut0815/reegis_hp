__copyright__ = "Uwe Krien"
__license__ = "GPLv3"


import weather
import powerplants as pp
import feedin
import configuration as config
from oemof.tools import logger


def run():
    """pass"""
    paths, pattern, files, general = config.get_configuration()

    # Store weather data
    if not general['skip_weather']:
        weather.fetch_coastdat2_year_from_db(paths['weather'],
                                             paths['geometry'],
                                             pattern['weather'],
                                             files['region_geometry'],
                                             overwrite=general['overwrite'])

        # Calculate the average wind speed for all available weather data sets.
        weather.get_average_wind_speed(paths['weather'],
                                       files['grid_geometry'],
                                       paths['geometry'],
                                       pattern['weather'],
                                       files['average_wind_speed'])

    if not general['skip_conv_power_plants']:
        pp.prepare_conventional_power_plants(paths, pattern,
                                             overwrite=general['overwrite'])

    if not general['skip_re_power_plants']:
        pp.prepare_re_power_plants(paths, pattern,
                                   overwrite=general['overwrite'])

    if not general['skip_feedin_weather']:
        feedin.normalised_feedin_by_weather(paths, pattern, files,
                                            overwrite=general['overwrite'])
    if not general['skip_feedin_region']:
        feedin.normalised_feedin_by_region(paths, pattern,
                                           overwrite=general['overwrite'])


if __name__ == "__main__":
    # initialise logger
    logger.define_logging()
    run()
