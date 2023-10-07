from fastapi import FastAPI
from pydantic import BaseModel,Field

from pytickersymbols import PyTickerSymbols

import os

import src.eurex as optex
import settings as _settings

from deta import Deta

try:
    deta_key = os.environ.get('eurex_base',_settings.settings.eurex_base)
except:
    print('set Environment variable >>> eurex_base <<< to access key for Deutsche Boerse API')  

# Connect to Deta Base with your Data Key
deta = Deta(deta_key)

db = deta.Base("eurex_base")

app = FastAPI()



@app.get("/")
async def root():
    return {"message": "Welcome to share evaluation, for API go to /docs"}

@app.get("/feed",tags=['database'],description='Initialize or update Database with Symbols and its members')
async def feed_base():
# create database in deta
# GLOBAL Data
    SYMBOLS = optex.create_repos()  # repo by name, symbols is dict symbol -> name
    # loop over name and create/update database
    for sym in SYMBOLS:
        print(sym)
        #db.put(sym)
    return SYMBOLS

@app.get("/feed_from_file",tags=['database'],description='update Database from file, if exists (faster)')
async def feed_from_file():
# create database in deta from json file (faster, but maybe outdated)
# GLOBAL Data
    SYMBOLS=optex.load_repos()
    return SYMBOLS
    # loop over name and create/update database

@app.get("/get_allsymbols",tags=['database'],description='return all keys for database')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_allsymbols():
    keysall = []
    for contry in ['DE','FR','NL','GB','IT','BE','CH','ES','IE','LU','FI']:
        data = db.fetch({"underlying_isin?pfx":contry}) # fetch prefix contry
        keysall.extend ([it['key'] for it in data.items]) # add items' key to global list keysall
        
    return keysall

@app.put("/update_allsymbols",tags=['database'], description='Update all database with lastprices, rent and yearpoint')
#update prices and rents on all symbols
async def update_allsymbols():
    keysall = await get_allsymbols()
    for key in keysall:
        try:
            check = await update_symbol(key)
        except:
            print(f'Updating {key} creates error ')
    return {'message':'updates OK'}




@app.get("/get_symbol",tags=['database'],description='return database entries for symbol')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_symbol(symbol: str='DTE'):
    data = db.get(symbol)
    return data

@app.put("/update_symbol",tags=['database'],description='get existing data from key, if exist update price, rent and yearpoint')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
# add info on date, rentabs, rentrel, yearpoint
async def update_symbol(symbol: str='DTE'):
    data = db.get(symbol)
    if data:
        _yahoo = data['yahoo']
        #history = optex.get_history(_yahoo,period='5d')
        #future  = optex.create_future(history)
        
        share_name,lastdate,lastprice,rent = optex.get_current_rent(_yahoo)
        #lastdate = history.dates.max()  
        #lastprice = history.loc[history.dates==lastdate].Close.values[0]
        ret = rent/lastprice *100
        data['lastdate']=lastdate
        data['lastprice']=lastprice
        data['rent_abs'] = rent
        data['rent_rel'] = ret
        yearpoint = await get_symbol_yearpoint(symbol)
        data.update(yearpoint)
        myreturn = db.put(data,key=symbol)
        return myreturn
    else:
        return {'error': f'key {symbol} not found'}



@app.get("/get_symbol_yahoo",tags=['database'],description='get yahoo key for symbol')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_symbol_yahoo(symbol: str='DTE'):
    data = await get_symbol(symbol)
    return data['yahoo']

@app.get("/get_symbol_google",tags=['database'],description='get google key for symbol')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_symbol_google(symbol: str='DTE'):
    data = await get_symbol(symbol)
    return data['google']


################################## from google and yahoo.  # 
# share data
# history data ( not saved, only in buffer)
@app.get("/get_history",tags=['database','yahoo'],description='get 2y history for symbol from yahoo')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_history(symbol: str='DTE',period: str='2y'):
    _yahoo = await get_symbol_yahoo(symbol)
    history = optex.get_history(_yahoo,period=period)#optex.get_yahoo_symb(symbol))
    return history.to_dict()

@app.get("/get_last_price",tags=['database','yahoo'],description='get last price for symbol')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_last_price(symbol: str='DTE'):
    _yahoo = await get_symbol_yahoo(symbol)
    history = optex.get_history(_yahoo,period='5d')#optex.get_yahoo_symb(symbol))
    last_price = history.iloc[-1]
    return {'date':last_price.dates,'Close':last_price.Close}
#
#
###### under construction ################

@app.get("/get_eurex_yearpoint",tags=['database','margins'],description='get margin in percent for call and put at market price for symbol (Measure for Volatility)')
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_symbol_yearpoint(symbol: str):
    df = await symbol_margins(symbol)
    last_price_date = await get_last_price(symbol)
    last_price = last_price_date['Close']
    # dict with maturity : (call margin %, put margin %)
    df['rel_strike']= df.exercise_price/last_price
    df['rel_margin']= df.premium_margin/(last_price*100) # contract size 100
    df['deviation'] = abs(df['rel_strike']-1.)
    
    year_point = optex.get_yearpoint(df,last_price) 
    #mat_dates = market_prices.keys()
    return  {'maturity_date':int(year_point[0]),
             'reference_price': float(last_price),
             'call_yp':float(year_point[1]),
             'put_yp':float(year_point[2])}


def get_margins(option_set):
    resp =optex.get_portfolio_margins(option_set)
    df = optex.df_from_portfolio(resp)
    return df

@app.get("/get_eurex_options",tags=['database','margins'],description='get all options (maturity and strikes) for a symbol (share)')
async def get_optionset(symbol: str):
    return optex.get_options(symbol)

async def symbol_margins(symbol: str):
    option_set =  await get_optionset(symbol)
    df = get_margins(option_set)
    return df

@app.get("/get_eurex_margins",tags=['database','margins'],description='get all options prices (maturity and strikes) for a symbol (share)')
async def get_symbol_margins(symbol: str):
    df = await symbol_margins(symbol)
    return df.to_dict(orient='tight')


@app.get("/get_eurex_symbols",tags=['database','margins'],description='get all options symbols available at EUREX')
async def get_eurex_symbols():
    # all dat, that have a yearpoint defined
    data = db.fetch({"call_yp?gte": 0})
    keys = [item['key'] for item in data.items]                    
    return keys


@app.get("/get_env",tags=['database'],description='get environment variable ')
async def get_env():
    # all dat, that have a yearpoint defined
    envs = [data for data in os.environ.items()]    
    return envs

# key rent data. (yearly and yearpoint, kurs und margin (?)) in second db? avoid rewrite of too many data

# refresh database (clean) from eurex and yahoo and google

# get data
# put data ( on schedule)
# delete data

#  extra app:
# create watchlists per user
# add row
# edit row (?)
# delete row
#
