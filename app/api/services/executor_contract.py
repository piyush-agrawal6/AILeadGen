"""Executor contract without importing or initializing the API scan manager."""
from abc import ABC,abstractmethod
from typing import Any,Dict,Optional

class ScanExecutor(ABC):
    @abstractmethod
    async def start(self,run_id:int,market:str,vertical:str,target:int,settings:Optional[Dict[str,Any]]=None)->None:pass
    @abstractmethod
    async def cancel(self,run_id:int)->bool:pass
    @abstractmethod
    async def resume(self,run_id:int)->bool:pass
    @abstractmethod
    def status(self,run_id:int)->Optional[str]:pass
