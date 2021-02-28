import asyncio
import  streamlit as st
import yfinance as yf
import math
import plotly.graph_objects as go
import pandas as pd
from plotly.subplots import make_subplots
import scipy.spatial.distance as dist_functions
from scipy.spatial.distance import cosine, euclidean, minkowski
from datetime import date, timedelta

# local imports 
import utils

max_width_str = f"max-width: 2000px;"
st.markdown(
    f"""
<style>
.reportview-container .main .block-container{{
    {max_width_str}
}}
</style>    
""",
    unsafe_allow_html=True,
)
# st.markdown(
#         f"""
# <style>
#     .reportview-container .main .block-container{{
#         max-width: {max_width}px;
#         padding-top: {padding_top}rem;
#         padding-right: {padding_right}rem;
#         padding-left: {padding_left}rem;
#         padding-bottom: {padding_bottom}rem;
#     }}
#     .reportview-container .main {{
#         color: {COLOR};
#         background-color: {BACKGROUND_COLOR};
#     }}
# </style>
# """,
#         unsafe_allow_html=True,
#     )

st.sidebar.title("Simple Pattern Finder")
st.sidebar.image("img/pattern.png")

symbol = st.sidebar.text_input(label='Symbol', value='SPY')


today = date.today()
delta = timedelta(days=50)
start = today - delta


start_date = st.sidebar.date_input(label='From :', value=start)
end_date = st.sidebar.date_input(label='To :')


ticker_info = yf.Ticker(symbol)
df = utils.fetch_data(symbol, start_date=start_date, end_date=end_date)

try:
    st.title(ticker_info.info['shortName'])
except :
    st.error('No data found, symbol may be delisted')
    st.stop()

fig = go.Figure(data=[go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],      
            close=df['Close'])]
      )

fig.update_xaxes(
    rangeslider_visible=True,
    rangebreaks=[
        dict(bounds=["sat", "mon"]),  # hide weekends, eg. hide sat to before mon
        dict(values=utils.get_holidays())  # hide holidays (Christmas and New Year's, etc)
    ]
)




st.sidebar.subheader("Pattern date range")
slice_start_date = st.sidebar.date_input(label='From :', value=end_date - timedelta(days=3), key="slice_start_date")
slice_end_date = st.sidebar.date_input(label='To :',  value=end_date, key="slice_end_date")


# fig.update_layout(title_text=slice_start_date.strftime("%Y-%m-%d") + "     " + slice_end_date.strftime("%Y-%m-%d"),
#                   title_font_size=20)

fig.update_layout(
    shapes=[
        dict(
            fillcolor="rgba(63, 81, 181, 0.2)",
            line={"width": 0},
            type="rect",
            x0=slice_start_date.strftime("%Y-%m-%d"),
            x1=slice_end_date.strftime("%Y-%m-%d"),
            xref="x",
            y0=0,
            y1=1,
            yref="paper"
        )
    ]
)
    
st.plotly_chart(fig, use_container_width=True)

distance_slb = st.sidebar.selectbox('Distance', ('cosine', 'euclidean', 'minkowski'))
distance = getattr(dist_functions, distance_slb)

num_of_outputs = st.sidebar.number_input(label='Max number of results', min_value=1, value=5)
find_btn = st.sidebar.button("Find similar patterns")


if find_btn:
    pattern = utils.df_to_normalized_vector(df[slice_start_date : slice_end_date])
    
    tickers = utils.liquid_stocks()

    workers = [utils.fetch(t) for t in tickers]
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    results = loop.run_until_complete(asyncio.gather(*workers))


    #Results
    similarity = []
    for r in results:
        if r:
            t = r['ticker']
            data = r['result']
            data_length = int(len(pattern) / 4)
            if len(data) < data_length: continue
            vector = utils.get_price_vector(data,last_days=data_length)
            similarity.append((t, distance(pattern, vector)))

   
    similarity.sort(key=lambda x: x[1])
   
   


    print(similarity[:5])
 
 
 
    # Plot results
    fig2 = make_subplots(
        rows=math.ceil(num_of_outputs / 2), 
        cols=2,
        column_widths=[0.5, 0.5],
        #row_heights=[0.4, 0.6],
        subplot_titles=list(map(lambda x : x[0], similarity[:num_of_outputs])),
        print_grid=False
    )

    fig2.update_xaxes(
        rangeslider_visible=False,
        rangebreaks=[
            dict(bounds=["sat", "mon"]),  # hide weekends, eg. hide sat to before mon
            dict(values=utils.get_holidays())  # hide holidays (Christmas and New Year's, etc)
        ]
    )

    fig2.update_layout(showlegend=False, width=800, height=1020)

    
    row, col = 1, 1
    for i, similar in enumerate(similarity[:num_of_outputs], start=1):
        symbol = similar[0]
        data = utils.get_ticker_data(symbol, results)
        df2 = pd.DataFrame(data)
        df2 = df2.iloc[-(int(len(pattern) / 4)*3):]
        fig2.add_trace(
            go.Candlestick(
                x=df2['datetime'],
                open=df2['open'],
                high=df2['high'],
                low=df2['low'],
                close=df2['close'],
            ), 
            row,
            col
        )

        col += 1
        
        if not (i % 2):
            col = 1
            row +=1

    st.subheader("Results")
    st.plotly_chart(fig2, use_container_width=True)