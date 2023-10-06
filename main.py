from fastapi import FastAPI
from pydantic import BaseModel,Field

from pytickersymbols import PyTickerSymbols

import os

import src.eurex as optex
import settings as _settings

from deta import Deta

deta_key = os.environ.get('eurex_base',_settings.settings.eurex_base)

# Connect to Deta Base with your Data Key
deta = Deta(deta_key)

db = deta.Base("eurex_base")

app = FastAPI()



@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/feed",tags=['database'])
async def feed_base():
# create database in deta
# GLOBAL Data
    SYMBOLS = optex.create_repos()  # repo by name, symbols is dict symbol -> name
    # loop over name and create/update database
    return SYMBOLS

@app.get("/feed_from_file",tags=['database'])
async def feed_from_file():
# create database in deta from json file (faster, but maybe outdated)
# GLOBAL Data
    SYMBOLS=optex.load_repos()
    return SYMBOLS
    # loop over name and create/update database

@app.get("/get_allsymbols",tags=['database'])
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_allsymbols():
    keysall = []
    for contry in ['DE','FR','NL','GB','IT','BE','CH','ES','IE','LU','FI']:
        data = db.fetch({"underlying_isin?pfx":contry})
        keysall.extend ([it['key'] for it in data.items])
        
    return keysall

@app.put("/update_allsymbols",tags=['database'])
#update prices and rents on all symbols
async def update_allsymbols():
    keysall = await get_allsymbols()
    for key in keysall:
        try:
            check = await put_symbol(key)
        except:
            print(f'Updating {key} creates error ')
    return {'message':'updates OK'}




@app.get("/get_symbol",tags=['database'])
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_symbol(symbol: str='DTE'):
    data = db.get(symbol)
    return data

@app.put("/put_symbol",tags=['database'])
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
# add info on date, rentabs, rentrel, yearpoint
async def put_symbol(symbol: str='DTE'):
    data = db.get(symbol)
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
    myreturn = db.put(data,key=symbol)
    return myreturn



@app.get("/get_symbol_yahoo",tags=['database'])
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_symbol_yahoo(symbol: str='DTE'):
    data = await get_symbol(symbol)
    return data['yahoo']

@app.get("/get_symbol_google",tags=['database'])
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_symbol_google(symbol: str='DTE'):
    data = await get_symbol(symbol)
    return data['google']


################################## from google and yahoo.  # 
# share data
# history data ( not saved, only in buffer)
@app.get("/get_history",tags=['database','yahoo'])
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_history(symbol: str='DTE',period: str='2y'):
    _yahoo = await get_symbol_yahoo(symbol)
    history = optex.get_history(_yahoo,period=period)#optex.get_yahoo_symb(symbol))
    return history.to_dict()

@app.get("/get_last_price",tags=['database','yahoo'])
#async def get_symbol(symbol: str = Field(default='DTE',description='Symbol for Option',min_length=3,max_length=4)): # creates an error . wait for new version
async def get_last_price(symbol: str='DTE'):
    _yahoo = await get_symbol_yahoo(symbol)
    history = optex.get_history(_yahoo,period='5d')#optex.get_yahoo_symb(symbol))
    last_price = history.iloc[-1]
    return {'date':last_price.dates,'Close':last_price.Close}


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
