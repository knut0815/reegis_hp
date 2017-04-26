import pandas as pd
import tools
import os
import geoplot
from matplotlib import pyplot as plt


def de21():
    """
    Plot of the de21 regions (offshore=blue, onshore=green).
    """
    my_df = pd.read_csv(
        os.path.join(os.path.dirname(__file__), 'data', 'geometries',
                     'polygons_de21.csv'),
        index_col='gid')

    label_coord = os.path.join(os.path.dirname(__file__),
                                     'data', 'geometries', 'coord_region.csv')

    offshore = geoplot.postgis2shapely(my_df.iloc[18:21].geom)
    onshore = geoplot.postgis2shapely(my_df.iloc[0:18].geom)
    plotde21 = geoplot.GeoPlotter(onshore, (3, 16, 47, 56))
    plotde21.plot(facecolor='#badd69', edgecolor='white')
    plotde21.geometries = offshore
    plotde21.plot(facecolor='#a5bfdd', edgecolor='white')
    tools.add_labels(my_df, plotde21, coord_file=label_coord,
                     textcolour='black')
    tools.draw_line(plotde21, (9.7, 53.4), (10.0, 53.55))
    plt.tight_layout()
    plt.box(on=None)
    plt.show()


if __name__ == "__main__":
    de21()
