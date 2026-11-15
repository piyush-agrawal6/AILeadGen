"""Request-local round-trip timings. Never stores SQL, parameters or identities."""
from contextvars import ContextVar
from dataclasses import dataclass,field
from threading import Lock
@dataclass
class Measurements:
    queries:int=0
    seconds:float=0
    lock:Lock=field(default_factory=Lock)
_active=ContextVar('request_database_measurements',default=None)
def begin():return _active.set(Measurements())
def finish(token):_active.reset(token)
def database(seconds):
    active=_active.get()
    if active:
        with active.lock:active.queries+=1;active.seconds+=seconds
def header():
    active=_active.get()
    if active is None:return ''
    with active.lock:return f'db;dur={active.seconds*1000:.1f};desc="{active.queries} statements"'
