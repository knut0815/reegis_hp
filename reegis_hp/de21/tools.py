import pandas as pd
import os
from matplotlib import pyplot as plt
import geoplot


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

plot_geocsv(os.path.join('geometries', 'federal_states3.csv'),
            idx_col='iso', coord_file='data_basic/label_federal_state.csv')


def read_seq_file():
    seq_file = 'scenarios/reegis_de_21_test_neu_seq.csv'
    seq_neu = 'scenarios/reegis_de_21_test_neu_neu_seq.csv'

    tmp_csv = pd.read_csv(seq_file, header=[0, 1, 2, 3, 4],
                          parse_dates=True, index_col=0)

    tmp_csv.to_csv(seq_neu)
    print(tmp_csv.index)
    

if __name__ == "__main__":
    plot_geocsv(os.path.join('geometries', 'federal_states3.csv'),
                idx_col='iso', coord_file='data_basic/label_federal_state.csv')
