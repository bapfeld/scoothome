import pandas as pd
from fbprophet import Prophet
from matplotlib.backends.backend_pdf import PdfPages

# need to get the data in
dat = pd.read_csv("/home/bapfeld/scoothome/data/jan_19_ts.csv")

# let's select the most complete time series...
area_list = list(dat.groupby('area')['n'].count().sort_values(ascending=False)[0:50].index)

# '3.0-48453000902'

with PdfPages('/home/bapfeld/scoothome/figures/estimation_by_area_jan.pdf') as pdf:
    for area in area_list:
        test_dat = dat[dat['area'] == area].copy().reset_index(drop=True)
        test_dat.drop(columns=['area'], inplace=True)
        test_dat.rename(columns={'time': 'ds', 'n': 'y'}, inplace=True)

        model = Prophet(changepoint_prior_scale=0.05)
        model.fit(test_dat)
        future = model.make_future_dataframe(periods=300, freq='H')
        fcst = model.predict(future)
        fig = model.plot(fcst)
        # fig.show()
        pdf.savefig()

        fig2 = model.plot_components(fcst)
        # fig2.show()
        pdf.savefig()

