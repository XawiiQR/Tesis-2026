import pandas as pd
import numpy as np

archivo = pd.read_csv('../data/PRSA_Data_Wanshouxigong_20130301-20170228.csv')
archivo.head()
print(archivo.columns)
print(archivo.info())
print(archivo.describe())