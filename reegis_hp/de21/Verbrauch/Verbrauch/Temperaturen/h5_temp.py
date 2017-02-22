import pandas as pd
import os


hdf = pd.HDFStore ("C:\\Users\olga\Desktop\Masterarbeit\Verbrauch\examples\Temperaturen\coastDat2_de_2013.h5", mode="r")

a = hdf.get('/A1129080')
del a ["dhi"]
del a ["dirhi"]
del a ["pressure"]
del a ["v_wind"]
del a ["z0"]

print(a)
results_path = 'results'
file_name = ("RE15.csv")
os.path.join(results_path, file_name)
a.to_csv(os.path.join(results_path, file_name))


