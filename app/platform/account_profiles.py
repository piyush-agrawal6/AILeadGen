"""Personal account preferences, independent of workspace roles and ownership."""
import hashlib
import json
from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
from pydantic import BaseModel,ConfigDict,Field,field_validator
from fastapi import HTTPException
from app.api.organization import ensure_user
from app.database.prospects import now


class AccountFields(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    display_name:str=Field(min_length=1,max_length=120)
    job_title:str=Field(default='',max_length=120)
    phone:str=Field(default='',max_length=50)
    timezone:str=Field(default='UTC',max_length=80)
    locale:str=Field(default='en',max_length=35,pattern=r'^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$')

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls,value):
        try:ZoneInfo(value)
        except (ZoneInfoNotFoundError,ValueError):raise ValueError('Choose a valid IANA timezone.') from None
        return value

    @field_validator('display_name','job_title','phone')
    @classmethod
    def printable(cls,value):
        if any(ord(ch)<32 for ch in value):raise ValueError('Control characters are not supported.')
        return value


class AccountUpdate(AccountFields):
    version:str=Field(min_length=64,max_length=64,pattern=r'^[a-f0-9]+$')


class AccountProfile(AccountFields):
    email:str
    version:str


def read(c,actor):
    row=c.execute('SELECT display_name,job_title,phone,timezone,locale,updated_at FROM user_profiles WHERE user_id=?',(actor,)).fetchone()
    user=c.execute('SELECT display_name FROM users WHERE id=?',(actor,)).fetchone()
    values={'display_name':(row['display_name'] if row else None) or (user[0] if user else None) or actor.split('@')[0],
        'job_title':(row['job_title'] if row else None) or '',
        'phone':(row['phone'] if row else None) or '',
        'timezone':(row['timezone'] if row else None) or 'UTC',
        'locale':(row['locale'] if row else None) or 'en'}
    digest=hashlib.sha256(json.dumps([actor,values,row['updated_at'] if row else None],sort_keys=True).encode()).hexdigest()
    return {**values,'email':actor,'version':digest}


def save(c,actor,body:AccountUpdate):
    ensure_user(c,actor)
    if getattr(c,'backend',None)=='postgres':c.execute('SELECT id FROM users WHERE id=? FOR UPDATE',(actor,))
    elif not c.in_transaction:c.execute('BEGIN IMMEDIATE')
    previous=read(c,actor)
    if previous['version']!=body.version:raise HTTPException(409,'Your profile changed. Reload it before saving.')
    fields=body.model_dump(exclude={'version'})
    if all(previous[key]==value for key,value in fields.items()):return previous
    stamp=now()
    c.execute('''INSERT INTO user_profiles(user_id,display_name,job_title,phone,timezone,locale,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET display_name=excluded.display_name,
        job_title=excluded.job_title,phone=excluded.phone,timezone=excluded.timezone,
        locale=excluded.locale,updated_at=excluded.updated_at''',
        (actor,fields['display_name'],fields['job_title'],fields['phone'],fields['timezone'],fields['locale'],stamp,stamp))
    c.execute('UPDATE users SET display_name=?,updated_at=? WHERE id=?',(fields['display_name'],stamp,actor))
    return read(c,actor)
