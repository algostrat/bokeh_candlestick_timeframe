#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =============================================================================
# To run app, open terminal in folder containing main.py
# and run:
#     bokeh serve --show main.py
# =============================================================================

import yfinance as yf
import pandas as pd
import numpy as np

from bokeh.layouts import column, row
from bokeh.models import HoverTool, CrosshairTool, Spinner, Div
from bokeh.plotting import ColumnDataSource, figure
from bokeh.models import Panel, Tabs, DatePicker, Select, TextInput
from bokeh.palettes import d3
from bokeh.io import curdoc

from datetime import date, timedelta

from functools import partial

ticker_symbols = {
    'DJI': '^DJI',
    'S&P 500': '^GSPC'
}


def yf_fund(ticker, start_date, end_date, principal):
    ticker_label = ticker

    if ticker in ticker_symbols.keys():
        ticker = ticker_symbols[ticker]

    yf_fund_ticker = yf.Ticker(ticker)
    end_date += timedelta(1)
    end_date = str(end_date)
    start_date = str(start_date)

    df_yf_fund = pd.DataFrame()
    df_yf_fund = yf_fund_ticker.history(start=start_date, end=end_date)
    df_yf_fund = df_yf_fund.groupby(df_yf_fund.index).first() #drops duplicates dates from after hours trading

    yf_fund_cost_basis = df_yf_fund.iloc[0, 0]
    no_shares = principal/yf_fund_cost_basis

    df_yf_fund['No. Shares'] = no_shares + \
        (no_shares * df_yf_fund['Stock Splits'])
    df_yf_fund['Position'] = df_yf_fund.Close * no_shares
    df_yf_fund['legend'] = ticker_label
    df_yf_fund.columns = [f'Stock {i}' for i in df_yf_fund.columns]

    return df_yf_fund, yf_fund_cost_basis


def managed_fund(principal, current_value, df_yf_fund):
    start_date = df_yf_fund.index[0]
    end_date = df_yf_fund.index[-1]
    period = (end_date - start_date).days
    period_years = period/365
    rate = ((current_value/principal)**(1/period_years)) - 1

    df_managed_fund = pd.DataFrame()
    df_managed_fund['Date'] = [(start_date + timedelta(i))
                               for i in range(period + 1)]
    df_managed_fund.Date = pd.to_datetime(df_managed_fund.Date)
    df_managed_fund['Position'] = [principal *
                                   (1 + rate) ** (i/365) for i in range(period + 1)]
    df_managed_fund = df_managed_fund[df_managed_fund.Date.isin(
        df_yf_fund.index.values)]
    df_managed_fund = df_managed_fund.set_index('Date')
    df_managed_fund['legend'] = 'Managed Fund'
    df_managed_fund.columns = [
        f'Managed {i}' for i in df_managed_fund.columns]

    return df_managed_fund, rate


def create_source(df_fund1, df_fund2):
    df_source = pd.DataFrame()
    df_fund1.index = pd.to_datetime(df_fund1.index)
    df_fund2.index = pd.to_datetime(df_fund2.index)

    legend1 = [i for i in df_fund1.columns if 'legend' in i][0]
    legend2 = [i for i in df_fund2.columns if 'legend' in i][0]

    df_fund1 = df_fund1.rename(columns={legend1: 'legend1'})
    df_fund2 = df_fund2.rename(columns={legend2: 'legend2'})

    col1 = [i for i in df_fund1.columns if 'Position' in i][0]
    col2 = [i for i in df_fund2.columns if 'Position' in i][0]

    df_source = df_fund1.join(df_fund2, how='inner', rsuffix='_2')
    df_source['Difference'] = df_fund1[col1] - df_fund2[col2]

    return df_source


def make_plot(df_source, title):
    source = ColumnDataSource(df_source)
    position_col = [i for i in df_source.columns if 'Position' in i]

    position1 = position_col[0]
    position2 = position_col[1]

    labels = [x.strip() for x in title.split('vs.')]
    label1 = labels[0]
    label2 = labels[1]

    TOOLTIPS = [
        ('Date', '@Date{%F}'),
        (label1, f'@{{{position1}}}{{$0,0}}'),
        (label2, f'@{{{position2}}}{{$0,0}}'),
        ('Difference', '@Difference{$0,0}'),
    ]

    plot = figure(width_policy='fit', height_policy='fit',
                  x_axis_type='datetime', title=title)
    plot.line('Date', position1, source=source, legend_field='legend1',
              color=d3['Category10'][10][0], line_width=3)
    plot.line('Date', position2, source=source, legend_field='legend2',
              color=d3['Category10'][10][1], line_width=3)
    plot.add_tools(CrosshairTool())
    plot.add_tools(HoverTool(tooltips=TOOLTIPS,
                             formatters={'@Date': 'datetime'}))
    plot.legend.location = 'top_left'
    plot.legend.click_policy = 'hide'
    plot.xaxis.axis_label = 'Date'
    plot.yaxis.axis_label = 'USD ($)'

    return plot, source


def div_text(df_source, cost_basis, investment_type):
    legend_col = [i for i in df_source.columns if 'legend' in i]
    legend1 = legend_col[0]
    ticker1 = df_source[legend1][0]
    legend2 = legend_col[1]
    ticker2 = df_source[legend2][0]

    position_col = next(i for i in df_source.columns if 'Position' in i)
    current_value = df_source[position_col][-1]
    principal = df_source[position_col][0]

    growth = (current_value - principal)/principal
    verb = 'appreciated' if growth > 0 else 'depreciated'
    difference = df_source['Difference'][-1] * -1
    if (type(cost_basis) == np.float64):
        cost_basis = f'{cost_basis: .2f}/share'

    text = (
        f'Your {investment_type} {verb} {growth: .0%}.'
        f'<br>If you invested in {ticker2}, you would have {difference:+.2f}.'
        f'<br>Cost basis for {ticker1}: {cost_basis}.'
    )

    return text


def update(attr, old, new, tab_no):
    start_date = pd.to_datetime(start_date_picker[tab_no].value).date()
    end_date = pd.to_datetime(end_date_picker[tab_no].value).date()
    principal = principal_spinner[tab_no].value
    current_value = current_value_spinner[tab_no].value
    min_date = find_min_date(tab_no)
    start_date_picker[tab_no].min_date = min_date

    if start_date < min_date:
        start_date_picker[tab_no].value = min_date
        start_date = min_date

    if tab_no == 1:
        df_fund_2[1], index_cost_basis = yf_fund(
            fund_2[1].value, start_date, end_date, principal)
        df_fund_1[1], rate = managed_fund(
            principal, current_value, df_fund_2[1])
        df_source[1] = create_source(df_fund_1[1], df_fund_2[1])

        new_source = ColumnDataSource(df_source[1])
        source[tab_no].data.update(new_source.data)
        div[tab_no].text = div_text(df_source[1], 'N/A', 'managed fund')

    else:
        df_fund_1[tab_no], stock_cost_basis = yf_fund(
            fund_1[tab_no].value, start_date, end_date, principal)
        df_fund_2[tab_no], stock2_cost_basis = yf_fund(
            fund_2[tab_no].value, start_date, end_date, principal)
        df_source[tab_no] = create_source(
            df_fund_1[tab_no], df_fund_2[tab_no])

        new_source = ColumnDataSource(df_source[tab_no])
        source[tab_no].data.update(new_source.data)
        div[tab_no].text = div_text(
            df_source[tab_no], stock_cost_basis, f'{fund_1[tab_no].value} investment')


def find_min_date(tab_no):
    if tab_no == 1:
        ticker = ticker_symbols[fund_2[tab_no].value]
        min_date = yf.Ticker(ticker).history(
            period='max').head(1).index[0].date()

    elif tab_no == 2:
        min_date_top = yf.Ticker(fund_1[tab_no].value).history(
            period='max').head(1).index[0].date()
        ticker = ticker_symbols[fund_2[tab_no].value]
        min_date_bottom = yf.Ticker(ticker).history(
            period='max').head(1).index[0].date()
        min_date = max(min_date_top, min_date_bottom)

    elif tab_no == 3:
        min_date_top = yf.Ticker(fund_1[tab_no].value).history(
            period='max').head(1).index[0].date()
        min_date_bottom = yf.Ticker(fund_2[tab_no].value).history(
            period='max').head(1).index[0].date()
        min_date = max(min_date_top, min_date_bottom)

    return min_date

# WIDGETS


principal = 1000.0
current_value = 3000.0
ticker = 'S&P 500'
start_date = date(2016, 5, 3)
end_date = date(2021, 5, 7)
max_date = yf.Ticker(ticker_symbols[ticker]).history(
    period='max').index[-1].date()

# Dictionary to store the widgets from each tab
start_date_picker = {}
end_date_picker = {}
principal_spinner = {}
current_value_spinner = {}
fund_1 = {}
fund_2 = {}

fund_1[1] = None
fund_2[1] = Select(title='Index', value='S&P 500',
                   options=['DJI', 'S&P 500'])

fund_1[2] = TextInput(value="AMZN", title="Stock Ticker Symbol")
fund_2[2] = Select(title='Index', value='S&P 500',
                   options=['DJI', 'S&P 500'])

fund_1[3] = TextInput(value="AMZN", title="Stock Ticker Symbol")
fund_2[3] = TextInput(value="GOOG", title="Stock 2 Ticker Symbol")

for i in [1, 2, 3]:
    start_date_picker[i] = DatePicker(title='Start Date', value=start_date, min_date=find_min_date(i),
                                      max_date=max_date)  # , min_date="2019-08-01", max_date="2019-10-30")
    end_date_picker[i] = DatePicker(title='End Date', value=end_date, min_date=find_min_date(i),
                                    max_date=max_date)
    principal_spinner[i] = Spinner(
        value=principal, step=1, title='Principal')
    current_value_spinner[i] = Spinner(
        value=current_value, step=1, title='Current Value')

# Dicitonaries to store dataframes/CDS that populate each tab
df_fund_1 = {}
df_fund_2 = {}
df_source = {}
source = {}
div = {}

# Tab 1
# Data

df_fund_2[1], index_cost_basis = yf_fund(
    fund_2[1].value, start_date, end_date, principal)
df_fund_1[1], rate = managed_fund(principal, current_value, df_fund_2[1])
df_source[1] = create_source(df_fund_1[1], df_fund_2[1])

# Set-up Plots

plot1, source[1] = make_plot(df_source[1], 'Managed Fund vs. Index')
div[1] = Div(text=div_text(df_source[1], 'N/A', 'managed fund'),
             sizing_mode='stretch_width', height=100)

# Layout

inputs = column(principal_spinner[1], current_value_spinner[1], fund_2[1], start_date_picker[1],
                end_date_picker[1], div[1])
tab_managed = Panel(child=row(plot1, inputs),
                    title='Managed Fund vs Index')

# Tab2
# Data

df_fund_1[2], stock_cost_basis = yf_fund(
    fund_1[2].value, start_date, end_date, principal)
df_fund_2[2], index_cost_basis = yf_fund(
    fund_2[2].value, start_date, end_date, principal)
df_source[2] = create_source(df_fund_1[2], df_fund_2[2])

# Plots

plot2, source[2] = make_plot(df_source[2], 'Stock vs. Index')
current_value_stock = df_source[2]['Stock Position'][-1]
div[2] = Div(text=div_text(df_source[2], stock_cost_basis, f'{fund_1[2].value} investment'),
             sizing_mode='stretch_width', height=100)
# Layout

inputs_stock = column(principal_spinner[2], fund_1[2], fund_2[2], start_date_picker[2],
                      end_date_picker[2], div[2])
tab_stock = Panel(child=row(plot2, inputs_stock), title='Stock vs Index')

# Tab3
# Data

df_fund_1[3], stock_cost_basis = yf_fund(
    fund_1[3].value, start_date, end_date, principal)
df_fund_2[3], stock2_cost_basis = yf_fund(
    fund_2[3].value, start_date, end_date, principal)
df_source[3] = create_source(df_fund_1[3], df_fund_2[3])

# Plot

plot3, source[3] = make_plot(df_source[3], 'Stock vs. Stock 2')
current_value_stock2 = df_source[3][f'Stock Position'][-1]
div[3] = Div(text=div_text(df_source[3], stock_cost_basis, f'{fund_1[3].value} investment'),
             sizing_mode='stretch_width', height=100)

# Layout

inputs_stock2 = column(
    principal_spinner[3], fund_1[3], fund_2[3], start_date_picker[3], end_date_picker[3], div[3])
tab_stock2 = Panel(child=row(plot3, inputs_stock2),
                   title='Stock vs Stock 2')
layout = Tabs(tabs=[tab_managed, tab_stock, tab_stock2])

for i in [1, 2, 3]:
    start_date_picker[i].on_change('value', partial(update, tab_no=i))
    end_date_picker[i].on_change('value', partial(update, tab_no=i))
    principal_spinner[i].on_change('value', partial(update, tab_no=i))
    current_value_spinner[i].on_change('value', partial(update, tab_no=i))

    fund_2[i].on_change('value', partial(update, tab_no=i))
    if i != 1:
        fund_1[i].on_change('value', partial(update, tab_no=i))

curdoc().add_root(layout)