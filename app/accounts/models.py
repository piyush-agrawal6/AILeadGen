from uuid import UUID
from pydantic import BaseModel,ConfigDict,Field,SecretStr,field_validator
from app.accounts.policy import normalize,work_email
from app.accounts.passwords import validate

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=False,hide_input_in_errors=True)
class Email(Strict):
    email:str=Field(max_length=254)
    @field_validator('email')
    @classmethod
    def email_address(cls,value):return normalize(value)
class Signup(Email):
    password:SecretStr=Field(repr=False,exclude=True)
    name:str=Field(min_length=1,max_length=120)
    company_name:str=Field(min_length=2,max_length=120)
    terms_version:str=Field(min_length=1,max_length=100)
    accepted_terms:bool
    request_id:UUID
    invitation_token:SecretStr|None=Field(None,repr=False,exclude=True)
    @field_validator('email')
    @classmethod
    def work_address(cls,value):return work_email(value)
    @field_validator('password')
    @classmethod
    def strong_password(cls,value):validate(value.get_secret_value());return value
    @field_validator('name','company_name')
    @classmethod
    def clean_text(cls,value):
        if not value.strip() or any(ord(ch)<32 for ch in value):raise ValueError('Enter a name without control characters.')
        result=value.strip()
        if len(result)<2:raise ValueError('Enter at least two characters.')
        return result
class Verify(Strict):
    challenge_id:UUID
    capability:SecretStr=Field(repr=False,exclude=True)
    code:SecretStr=Field(repr=False,exclude=True)
class Resend(Strict):
    challenge_id:UUID
    capability:SecretStr=Field(repr=False,exclude=True)
    request_id:UUID
class Login(Email):
    password:SecretStr=Field(repr=False,exclude=True)
class Recovery(Email):
    request_id:UUID
class Reset(Strict):
    token:SecretStr=Field(repr=False,exclude=True)
    password:SecretStr=Field(repr=False,exclude=True)
    @field_validator('password')
    @classmethod
    def strong_password(cls,value):validate(value.get_secret_value());return value

class Exchange(Strict):
    token:SecretStr=Field(repr=False,exclude=True)
class SetPassword(Strict):
    password:SecretStr=Field(repr=False,exclude=True)
    request_id:UUID
    @field_validator('password')
    @classmethod
    def strong_password(cls,value):validate(value.get_secret_value());return value
class AcceptTerms(Strict):
    terms_version:str=Field(min_length=1,max_length=100)
    accepted:bool
    request_id:UUID
