import pandas as pd
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

dat = pd.read_csv('/home/bapfeld/scoothome/data/nano_ts.csv')
dat.set_index('time', inplace=True)

fig, ax = plt.subplots(figsize=(20, 5))
dat.groupby('area')['n'].plot()
fig.show()

plt.close()

# want to subset to only include non-zero areas?


with PdfPages('/home/bapfeld/scoothome/figures/time_series_by_area.pdf') as pdf:
    for i in range(areas):
        subset = dat
        plt.figure(figure=(11, 5))
        subset.groupby('area')['n'].plot()
        plt.title()
        pdf.savefig()
        plt.close()
