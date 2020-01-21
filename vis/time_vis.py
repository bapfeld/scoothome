import pandas as pd
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

dat = pd.read_csv('/home/bapfeld/scoothome/data/sample_full_list.csv')
dat.set_index('time', inplace=True)
dat.sort_index()

fig, ax = plt.subplots(figsize=(20, 5))
dat.groupby('area')['n'].plot()
fig.show()

plt.close()

# want to subset to only include non-zero areas?

areas = pd.unique(dat['area'])
with PdfPages('/home/bapfeld/scoothome/figures/time_series_by_area.pdf') as pdf:
    for i in range(len(areas)):
        subset = dat[dat['area'] == areas[i]]
        # subset.sort_values()
        plt.figure(figsize=(11, 5))
        subset.plot()
        plt.title(areas[i])
        pdf.savefig()
        plt.close()
