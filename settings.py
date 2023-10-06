from typing import Union

from pydantic import Field
from pydantic_settings import BaseSettings,SettingsConfigDict

# 
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')
    #api_key: Union[str,None] = Field(default=None,alias='my_api_key')      
    eurex_margins : Union[str,None] = Field(default=None)#,alias='eurex_api_key')  
    eurex_base : Union[str,None] = Field(default=None)#,alias='deta_api_key')  

settings=Settings()#_env_file='secrets.env' , _env_file_encoding='utf-8')
