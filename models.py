from sqlalchemy import Column, String, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid
from pydantic import BaseModel, EmailStr
from typing import  Dict,Optional,List
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False, unique=True)
    phone = Column(String(15), nullable=False, unique=True)
    password = Column(String(255), nullable=False)
    form_data = Column(JSON, nullable=True)
    subscription = Column(String(10), nullable=True)
    
class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    token: str
    token_type: str

class TokenStatus(BaseModel):
    status: str 

class GetForm(BaseModel):
    status: str
    form_json: Optional[Dict] = None
    settings: Optional[Dict] = None
    message: Optional[str] = None
    
class CreateForm(BaseModel):
    form_json: Dict
    settings: Dict
    active: bool
    scheduled: bool
    start: Optional[datetime]
    end: Optional[datetime]
    
class CreateFormReponse(BaseModel):
    message: str
    form_id: str

class AddTemplate(BaseModel):
    form_json:dict
    categories:List
    title:str
    description:str
    by_name:str
    by_id:str
    
class AddTemplateResponse(BaseModel):
    message:str
    
class Template(BaseModel):
    id: str
    publisher_name: str
    publisher_id: str
    title: str
    description: str
    form_json: dict
    categories: List[str]

class GetTemplatesResponse(BaseModel):
    templates: List[Template]
    
class Contact(BaseModel):
    name:str
    phone:str
    message:str
    email:str

class ContactResponse(BaseModel):
    message:str