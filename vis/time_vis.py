import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

dat = pd.read_csv('/home/bapfeld/scoothome/data/nano_ts.csv')
dat.set_index('time', inplace=True)

fig, ax = plt.subplots(figsize=(20, 5))
dat.groupby('area')['n'].plot()
fig.show()

plt.close()
