# -*- coding: utf-8 -*-
"""
Created on Mon Jul  8 18:49:41 2024

TO GET FAIR VALUE GAP (FVG) AND PLACE TRADES BASED ON THAT

@author: LK
"""

# IMPORT LIBRARIES

import MetaTrader5 as mt5
import numpy as np
import datetime
import pandas as pd
import pytz
import pandas_ta as ta
from time import sleep


# news_zone = 'GB'
# news_zone = 'EU'
# news_zone = 'US'
news_zone = 'ALL2'
# news_zone = 'NEW'
# news_zone = 'CC'

if news_zone == 'GB':
    currs = ['GBPJPY','GBPUSD', 'EURUSD','EURGBP']
elif news_zone == 'EU':
    currs = [ 'EURUSD', 'EURGBP']
elif news_zone == 'ALL':
    currs = ['GBPJPY','GBPUSD', 'EURUSD', 'EURGBP', 'USDJPY', 'XAUUSD', 
             'USDCAD', 'AUDUSD', 'BTCUSD', 'NZDUSD']
elif news_zone == 'CC':
    currs = ['BTCUSD', 'ETHUSD', 'DOGUSD', 'SOLUSD']
elif news_zone == 'ALL2':    
    currs = ['AUDCAD', 'AUDCHF', 'AUDJPY', 'AUDNZD', 'AUDUSD', 'CADCHF', 'CADJPY', 'CHFJPY', 'GBPAUD', 'GBPCAD', 
               'GBPCHF', 'GBPJPY', 'GBPNZD', 'GBPUSD', 'EURAUD', 'EURCAD', 'EURCHF', 'EURGBP', 'EURJPY', 'EURNZD',
               'EURUSD', 'NZDCAD', 'NZDCHF', 'NZDJPY', 'NZDUSD', 'USDCAD', 'USDCHF', 'USDCNH', 'USDJPY', 'XAUUSD']#, 'BTCUSD']

else:
    currs = ['AUDUSD','GBPUSD', 'NZDUSD','XAUUSD']


# SET THE NEWS TIME
news_min = 7
news_hour = 23

close_case = 0
pct_diff = 5 # 0.00001
period = 10
man_tp = 200
man_sl = -200
DD = 0
DU = 0

time_frame = 5
i = 20 # FVG in points

# LOGIN TO MT5
account = 51962256
mt5.initialize("C:/Program Files/FxPro - MetaTrader 5/terminal64.exe")
authorized=mt5.login(account, password="1nojf!W@MEUAz8", server = "mt5-demo.icmarkets.com")

if authorized:
    print("Connected: Connecting to MT5 Client")
else:
    print("Failed to connect at account #{}, error code: {}"
          .format(account, mt5.last_error()))
   
# establish connection to MetaTrader 5 terminal
if not mt5.initialize():
    print("initialize() failed, error code =",mt5.last_error())
    mt5.shutdown()
    
tz = pytz.timezone("Europe/London")
mt5_now = datetime.datetime.fromtimestamp(mt5.symbol_info('GBPUSD').time)
news_time = datetime.datetime.now(tz).replace(hour=news_hour, minute=news_min, second =0)

prev_positions = 0
# news_time = datetime.datetime.now(tz).replace(hour=news_hour, minute=news_min, second =0)
# news_time = datetime.datetime.now(tz).replace(hour=datetime.datetime.now(tz).hour + 1, minute=0, second =0)


# ALL FUNCTIONS
def get_rates(curr_pair, rate_type, time_frame):
    
    # point = mt5.symbol_info(curr_pair).point
    if rate_type == 1:
    # RATES FOR 10% OF DAY TICKS #### BID ASK
        utc_to = datetime.datetime.fromtimestamp(mt5.symbol_info(curr_pair).time)
        utc_from = utc_to - datetime.timedelta(hours=0.1)
        rates = mt5.copy_ticks_range(curr_pair, utc_from, utc_to, mt5.COPY_TICKS_ALL) # COPY_TICKS_INFO
        rates_frame = pd.DataFrame(rates)
        rates_frame['close'] = (rates_frame['ask'] + rates_frame['bid'])/2

        rates_frame['times'] = pd.to_datetime(rates_frame['time'], unit='s')
        rates_frame['mins'] = rates_frame['times'].dt.minute
        rates_frame['hrs'] = rates_frame['times'].dt.hour
        return rates_frame
    
    if rate_type == 2:
    # RATES FOR LAST 1000 BARS # OHLC
        # rates = mt5.copy_rates_from_pos(curr_pair, mt5.TIMEFRAME_M1, 0, 500)
        utc_to = datetime.datetime.fromtimestamp(mt5.symbol_info(curr_pair).time)
        utc_from = utc_to - datetime.timedelta(hours=5)
        rates = mt5.copy_rates_range(curr_pair, time_frame, utc_from, utc_to)
        rates_frame = pd.DataFrame(rates)
        # rates_frame['log_return'] = np.log(rates_frame['close']).diff()
        rates_frame['times'] = pd.to_datetime(rates_frame['time'], unit='s')
        rates_frame['mins'] = rates_frame['times'].dt.minute
        rates_frame['hrs'] = rates_frame['times'].dt.hour
        return rates_frame

def make_order(curr_pair, request, SL, TP, ord_price, comm):
        symbol = curr_pair
        lot = 1.0
        exp_time = datetime.datetime.fromtimestamp(mt5.symbol_info(curr_pair).time)
        time_diff = datetime.datetime.timestamp(exp_time + datetime.timedelta(minutes=300))

        deviation = 20
        tick = mt5.symbol_info_tick(symbol)
        symbol_info = mt5.symbol_info(symbol)
        point = mt5.symbol_info(symbol).point
        # time_diff = datetime.datetime.timestamp(tz2.localize(datetime.datetime.now()) + datetime.timedelta(0,500))
        
        if symbol_info is None:
            print(symbol, "not found, can not call order_check()")
            mt5.shutdown()
            quit()
         
        # if the symbol is unavailable in MarketWatch, add it
        if not symbol_info.visible:
            print(symbol, "is not visible, trying to switch on")
            if not mt5.symbol_select(symbol,True):
                print("symbol_select({}}) failed, exit",symbol)
                mt5.shutdown()
                quit()
         
        B_request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY_LIMIT,
            "price": ord_price, #if tick.ask < high else tick.ask + (5*point), #price,
            "sl": SL, # 0.0,#price - (120000 * point),
            "tp": TP,#price + (120000 * point),
            "deviation": deviation,
            "magic": 234000,
            "comment": comm, #"python script open",
            "type_time": mt5.ORDER_TIME_SPECIFIED, # ORDER_TIME_GTC,
            "expiration": round(time_diff),
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
         
        S_request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_SELL_LIMIT,
            "price": ord_price, # if tick.bid > low else tick.bid - (5*point), #price2,
            "sl": SL,#price + (120000 * point),
            "tp": TP,#price - (120000 * point),
            "deviation": deviation,
            "magic": 234000,
            "comment": comm, # "python script open",
            "type_time": mt5.ORDER_TIME_SPECIFIED, # ORDER_TIME_SPECIFIED,
            "expiration": round(time_diff),
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        
        if request == 1:
            result = mt5.order_send(B_request)
            if result.comment == "Request executed":
                print(result.request.symbol, " PENDING TRADE DONE ")
            
        elif request == 2:
            result = mt5.order_send(S_request)
            if result.comment == "Request executed":
                print(result.request.symbol, " PENDING TRADE DONE ")
            
            
        return result

def close_pending_order(order):
    
    request1={
        "order": order.ticket,
        "action": mt5.TRADE_ACTION_REMOVE,   
        }
    print ("CLOSE PENDING ORDER")
    mt5.order_send(request1)
    
def is_ranging_bollinger_bands(data, period=20, num_std_dev=2):
    upper_band, middle_band, lower_band = ta.bbands(data['close'], length=period, std=num_std_dev)
    # Check if the price stays within the Bollinger Bands
    is_ranging = (data['low'] > lower_band) & (data['high'] < upper_band)
    return is_ranging
    
    
def close_position(position):
    
        tick = mt5.symbol_info_tick(position.symbol)
    
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_BUY if position.type == mt5.ORDER_TYPE_SELL else mt5.ORDER_TYPE_SELL,
            "price": tick.ask if position.type == 1 else tick.bid,  
            "deviation": 20,
            "magic": 100,
            "comment": "python script close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
    
        result = mt5.order_send(request)
        print("CLOSE TRADE DONE - ", result.request.symbol)
        return result



sleep_t = 0.1
set_open_pos = 0
set_open_orders = 0
trade_time = datetime.datetime.now(tz)
trader = 0
# res_check = pd.DataFrame(columns = ['symbol', 'profit', 'drawUP', 'drawdown', 'trade_type'])
res_check = pd.DataFrame()

if time_frame == 15:
    time_frame = mt5.TIMEFRAME_M15
    i = i*3 # FVG in points
elif time_frame == 5:
    time_frame = mt5.TIMEFRAME_M5
    i = i*2 # FVG in points
elif time_frame == 1:
    time_frame = mt5.TIMEFRAME_M1
    i = i*1 # FVG in points
elif time_frame == 30:
    time_frame = mt5.TIMEFRAME_M30
    i = i*4 # FVG in points
elif time_frame == 60:
    time_frame = mt5.TIMEFRAME_H1
    i = i*5 # FVG in points


while datetime.datetime.now(tz).hour <= 26:
    # PAUSE ALL TRADES FROM 9PM TILL MIDNIGHT
    london_now = datetime.datetime.now(tz)
    if (len(mt5.positions_get()) < 1 and len(mt5.orders_get()) < 1 
        and datetime.datetime.now(tz).hour >= 25):
        print("ON SLEEP TILL LONDON MIDNIGHT")
        
        
        nyt = datetime.datetime.now(tz).replace(hour=23, minute=59, second =59)
        sleep_time = nyt - datetime.datetime.now(tz)
        
        sleep(sleep_time.seconds + 10)
    
    # PAUSE ALL TRADES AT HIGH IMPACT NEWS TIME
    if (datetime.datetime.now(tz) > news_time - datetime.timedelta(0,300) and # START BREAK 5 MINS BEFORE NEWS TIME
        datetime.datetime.now(tz) < news_time + datetime.timedelta(0,30)):
        print("SHUTDOWN ALL ORDERS OR DEALS MANUALLY")
        print("NEWSTIME BREAK ACTIVE...")    
        
        sleep(600) # SLEEP FOR 10 MINS; ENDS BREAK 5 MINS AFTER NEWS TIME
        
        # Calculate the minutes to add to round up to the next 5-minute interval
    minutes_to_add = (time_frame - london_now.minute % time_frame) % time_frame
    if minutes_to_add == 0:  # If already at a 5-minute mark, move to the next one
        minutes_to_add = time_frame
    rounded_time = (london_now + datetime.timedelta(minutes=minutes_to_add)).replace(second=0, microsecond=0)
    
    # Step 3: Calculate the time difference in seconds
    time_to_sleep = (rounded_time - london_now).total_seconds()
    print('On pause till: ', rounded_time)        
    sleep(time_to_sleep + 10)
        
# TO OPEN ORDER    
    for curr in currs:
        if (len(mt5.positions_get(symbol=curr)) < 1 
            and close_case == 0 and set_open_pos == 0 and datetime.datetime.now(tz).hour < 25):
            # and datetime.datetime.now(tz) >= news_time - datetime.timedelta(0,3) 
            #     and datetime.datetime.now(tz) < news_time + datetime.timedelta(0,7)
            #     ):
            point = mt5.symbol_info(curr).point    
            # i = 50 ### FV GAP
            resistance = 0
            support = 0
            # for curr in currs:
            rates_frame = get_rates(curr, 2, time_frame)
            
            new_df = rates_frame.iloc[rates_frame.shape[0]-4:].reset_index(drop=True)
            
            ### STRATEGY
            ### BUY SITUATION
            if new_df.iloc[-2]['low'] - new_df.iloc[-4]['high'] > (i * point):
                ord_price = new_df.iloc[-2]['low']
                SL = new_df.iloc[-4]['low']
                TP = ord_price + ((ord_price - SL) * 1)
                comm = 'FVG python'
                if len(mt5.orders_get(symbol=curr)) > 0:
                    
                    close_pending_order(mt5.orders_get(symbol=curr)[0])
                    
                ord1 = make_order(curr, 1, SL, TP, ord_price, comm)
                
            ### SELL SITUATION
            if new_df.iloc[-4]['low'] - new_df.iloc[-2]['high'] > (i * point):
                ord_price = new_df.iloc[-2]['high']
                SL = new_df.iloc[-4]['high']
                TP = ord_price - ((ord_price - SL) * 1)
                comm = 'FVG python'
                ord1 = make_order(curr, 2, SL, TP, ord_price, comm)
            

            mt5_hr = datetime.datetime.fromtimestamp(mt5.symbol_info(curr).time)
                       
            trade_time = datetime.datetime.now(tz)
   

# TO CLOSE ORDER

    #TAKE PROFIT
    for position in mt5.positions_get():
        if position.profit > DU:
            DU =  position.profit
            res = pd.DataFrame([position.symbol, position.profit, DU, DD, position.type])
        if position.profit < DD:
            DD =  position.profit
            res = pd.DataFrame([position.symbol, position.profit, DU, DD, position.type])
        if position.profit >= man_tp or position.profit <= man_sl:
            res_check = pd.concat([res.T, res_check], ignore_index=True)
            # res_check.columns = ['symbol', 'profit', 'drawUP', 'drawdown', 'trade_type']
            res_check.to_csv('fvg1.csv', index=False)
            DU = 0
            DD = 0
            close_result = close_position(position)
            

    # CLOSE ALL OPEN TRADES BY 5PM LONDON TIME
    if close_case == 5:
        positions = mt5.positions_get()
        for position in positions:
            close_result = close_position(position)
    
    # CLOSE PENDING ORDER ONCE ONE ORDER ACTIVATES OR 10AM HITS
    # if close_case == 10 :
    if datetime.datetime.now(tz)  > trade_time + datetime.timedelta(0,1200): # MANUAL EXPIRATION OF PENDING ORDERS
        # close_case = 10
        orders = mt5.orders_get()
        for order in orders:
            close_order = close_pending_order(order)
            
    if len(mt5.orders_get()) > 0:
        set_open_orders = 1
    
    if (len(mt5.positions_get()) < 1 and datetime.datetime.now(tz) > trade_time + datetime.timedelta(0,7)
            and set_open_pos > 0):
        set_open_pos = 0

    
# MULTIPLE CURRENCY PAIRS
# WHEN PENDING ORDER CHANGES TO POSITION

    if len(mt5.positions_get()) >= 1:
        for position in mt5.positions_get():
            pos_sym = position.symbol
            if len(mt5.orders_get()) > 0:
                for order in mt5.orders_get():
                    if order.symbol == pos_sym:
                        close_order = close_pending_order(order)
                        prev_positions = len(mt5.positions_get())
                        # set_open_pos = 1
                        
    
    print(london_now)
    sleep(sleep_t)
    
    if (len(mt5.positions_get()) < 1 and len(mt5.orders_get()) < 1):
        # and set_open_orders == 1):
        print("no active trades, closing...")
        set_open_orders = 0
        sleep(2)
        # break
    
    # CHECK IF TOTAL PROFIT ON ALL POSITION AND CLOSE 
    pt = pd.DataFrame(list(mt5.positions_get()),columns=mt5.positions_get()[0]._asdict().keys())
    # position_id = pt.ticket.item()
    t_profit = pt['profit'].sum()

    if t_profit > 1000 or t_profit < -1000:
        # closa = 0
        # c_loop = c_loop +1
        for position in positions:
            close_result = close_position(position)
    
    # # if datetime.datetime.now().minute >= 58:
    # news_time = datetime.datetime.now(tz).replace(hour=datetime.datetime.now(tz).hour + 1, minute=0, second =0)

    # if datetime.datetime.now(tz).hour < 13 and datetime.datetime.now(tz).hour >= 6:
    #     currs = ['AUDUSD','GBPUSD', 'NZDUSD','XAUUSD']
    #     # currs = ['GBPJPY','GBPUSD', 'EURUSD','EURGBP', 'BTCUSD', 'XAUUSD']
    # elif datetime.datetime.now(tz).hour < 6:
    #     currs = ['AUDUSD','GBPUSD', 'NZDUSD','XAUUSD']
    #     # currs = ['AUDUSD', 'NZDUSD', 'USDJPY', 'CADJPY', 'XAUUSD', 'BTCUSD']
    # elif datetime.datetime.now(tz).hour >= 13 and datetime.datetime.now(tz).hour <= 20:
    #     currs = ['AUDUSD','GBPUSD', 'NZDUSD','XAUUSD']
    #     # currs = ['GBPUSD', 'EURUSD', 'USDJPY', 'XAUUSD', 'BTCUSD']