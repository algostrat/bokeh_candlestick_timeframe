import pandas as pd
from bokeh.io import curdoc
from bokeh.plotting import figure, output_file, show
from bokeh.io import output_notebook
from bokeh.models import WheelZoomTool
import pandas as pd
from bokeh.layouts import column
from bokeh.plotting import figure, output_file, show
from bokeh.models import ColumnDataSource, CustomJS, Slider

# pulling tick data
df = pd.read_csv('https://raw.githubusercontent.com/algostrat/bokeh_candlestick_timeframe/50334c1a55d5aaf9a9df250ec450c4207c00fb25/may2020.csv',
                 parse_dates=['RateDateTime'],
                 index_col=['RateDateTime'])

timeframes = ['1min','5min','15min','30min','1h']


# How do I store the data in a columndatastore?

data = {} # dictionary of dataframes
data2 = {} # dictionary of dictionaries of lists
data3 = {} # dictionary lists for each column
tfs = timeframes
for tf in tfs:
    data[tf] =  df['RateBid'].resample(tf).ohlc()
    data[tf] = data[tf] 

    data2[tf] =  data[tf].reset_index().to_dict(orient='list') 
    data2[tf]['RateDateTime'] = [dobj.strftime('%Y-%m-%d %H:%M:%S') for dobj in data2[tf]['RateDateTime']]

    # create a flat table of time frame data
    for col in ['RateDateTime', 'open','high','low','close']:
        data3[(tf+'-'+col)] =  data2[tf][col]
tfDict = {i:tfs[i] for i in range(len(tfs))}



#server side callback 

def update_source():
    """Update the data source to be displayed.
    This is called once when the plot initiates, and then every time the slider moves, or a different instrument is
    selected from the dropdown.
    """
    newtf = tfDict[slider.value]

    # create new view from dataframe
    newdf = data[newtf]

    # create new source
    # new_source = df_view.to_dict(orient='list')

    # add colors to be used for plotting bull and bear candles
    colors = ['#D5E1DD' if cl >= op else '#F2583E' for (cl, op)
              in zip(newdf['close'], newdf['open'])]
    newdf['colors'] = colors
    newdf['width'] = pd.Timedelta(newtf)*.75

    # source.data.update(new_source)
    source.data = newdf

def slider_handler(attr, old, new):
    """Handler function for the slider. Updates the ColumnDataSource to a new range given by the slider's position."""
    update_source()

slider = Slider(start=1, end=(len(timeframes) -1) , value=2, step=1, title="Time frame")
slider.on_change('value', slider_handler)

# initialize the data source
source = ColumnDataSource()
update_source()

TOOLS = "pan,wheel_zoom,box_zoom,reset,save"

p = figure(
    x_axis_type="datetime", 
    tools=TOOLS, plot_width=1000, 
    sizing_mode="stretch_width",
    output_backend="webgl",
    width_policy='fit', height_policy='fit'
)

p.segment('RateDateTime', 'high', 'RateDateTime', 'low', source=source, line_width=1, color='black')  # plot the wicks
p.vbar('RateDateTime', 'width', 'close', 'open', source=source, line_color='black', fill_color='colors', )  # plot the body

p.toolbar.active_scroll = p.select_one(WheelZoomTool)
# p.segment(data15.index, data15.high, data15.index, data15.low, color="black")
# p.vbar(data15.index[inc], w, data15.open[inc], data15.close[inc], fill_color="#D5E1DD", line_color="black")
# p.vbar(data15.index[dec], w, data15.open[dec], data15.close[dec], fill_color="#F2583E", line_color="black")
p.toolbar.logo = None

curdoc().add_root(
    column(
        p,
        slider
    ))