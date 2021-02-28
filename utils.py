import asyncio
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf
import datetime
from datetime import timedelta

from yahoo_finance_async import OHLC
from yahoo_finance_async import History, Interval

from scipy.spatial.distance import cosine, euclidean
from typing import List


@st.cache
def fetch_data(symbol : str, start_date : datetime, end_date: datetime):
    ONE_DAY = timedelta(days=1)
    ticker = yf.Ticker(symbol)
    return ticker.history(start=start_date , end=end_date + ONE_DAY).copy()



def liquid_stocks(filename='liquid_stocks') -> List[str]: 
    with open(filename, 'r') as f:
        data = f.read()
        return sorted(data.split(' '))


def get_holidays() -> List[str]:
    HOLIDAYS_URL = "http://www.nasdaqtrader.com/trader.aspx?id=calendar"
    holidays_df = pd.read_html(HOLIDAYS_URL)[0]
    holidays_df.columns = ['Date', 'Holiday', 'Status']
    holidays_df = holidays_df[holidays_df['Status'] == 'Closed']
    holidays_df['Date'] = holidays_df['Date'].astype(np.datetime64)
    return list(holidays_df['Date'].apply(lambda d : f"{d.year}-{d.month}-{d.day}").values)


def df_to_normalized_vector(df : pd.DataFrame) -> List[float]:
    matrix = df[['Open', 'High', 'Low', 'Close']].values
    flatten = matrix.flatten()
    return list((flatten - flatten.mean()) / flatten.std())


async def fetch(ticker : str):
    try:
        res = await OHLC.fetch(ticker, interval=Interval.DAY, history=History.HALF_YEAR)
        return dict(ticker=ticker, result=res['candles'])
    except:
        return None


def get_ticker_data(ticker:str, data:list) -> dict:
    for d in data:
        if d and d['ticker'] == ticker:
            return d['result']

    return None


def get_price_vector(data, last_days=3):
    data = data[-last_days:]
    flatten = list()
    for d in data:
        flatten.extend([d['open'], d['high'], d['low'], d['close']])

    flatten = np.array(flatten)
    normalized = list((flatten - flatten.mean()) / flatten.std())
    return normalized


